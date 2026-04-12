import telebot
from telebot import types
from dotenv import load_dotenv
import socks  # <-- ДОБАВИТЬ ЭТУ СТРОКУ
import os
from database import db, User
from models import SendFlow, RequestFlow, registr_account_by_phone, checkDisposable, get_transfer_info, get_confirm

from urllib.parse import urlparse, parse_qs

# Загружаем переменные окружения
load_dotenv()

# НАСТРОЙКА ПРОКСИ (правильный способ для telebot)
from telebot import apihelper

# Настройка прокси для всех запросов telebot
apihelper.proxy = {
    'https': 'socks5://dd4482437e89f9af8929514eee7faaf61f@proxy99.madapp.cc:443'
}

# Создаем бота
bot = telebot.TeleBot(os.getenv('TELEGRAM_BOT_TOKEN'))
BOT_USERNAME = bot.get_me().username

def send_transfer_warning(cid: int, other_username: str, amount: str, is_request: bool = False):
    """
    Отправляет предупреждение о первом переводе между пользователями

    Args:
        cid: chat_id пользователя, которому отправляется предупреждение
        other_username: username второго участника перевода
        amount: сумма перевода
        is_request: True если это запрос, False если отправка
    """
    try:
        user = db.get_user_by_chat(cid)
        if not user or not user.username:
            return

        sender_username = user.username

        # Пропускаем проверку если это один и тот же пользователь
        if sender_username == other_username:
            return

        # Проверяем историю переводов
        has_previous = db.has_previous_transfers(sender_username, other_username)

        if not has_previous:
            if is_request:
                warning_text = (
                    f"⚠️ <b>Внимание!</b>\n\n"
                    f"Вы получили запрос на {amount} ₽ от @{other_username}, "
                    f"но у вас еще не было переводов с этим человеком.\n\n"
                    f"<i>Рекомендуем убедиться в надежности отправителя перед переводом.</i>"
                )
            else:
                warning_text = (
                    f"⚠️ <b>Внимание!</b>\n\n"
                    f"Вы отправляете перевод на {amount} ₽ пользователю @{other_username}, "
                    f"но у вас еще не было переводов с этим человеком.\n\n"
                    f"<i>Рекомендуем убедиться в надежности получателя перед переводом.</i>"
                )

            bot.send_message(cid, warning_text, parse_mode='HTML')
            print(f"Предупреждение отправлено {sender_username} о первом переводе с {other_username}")

    except Exception as e:
        print(f"Ошибка при отправке предупреждения: {str(e)}")

# Состояния
reg_temp: dict[int, str]              = {}
awaiting_reg: set[int]                = set()
send_state: dict[int, SendFlow]       = {}
request_state: dict[int, RequestFlow] = {}
changing_phone                        = set()

# Валидации
def is_valid_phone_manual(p: str) -> bool:
    return (p.startswith('+7') and len(p) == 12 and p[1:].isdigit()) \
        or (p.startswith('8') and len(p) == 11 and p.isdigit())

def is_valid_phone_contact(p: str) -> bool:
    return p.startswith('7') and len(p) == 11 and p.isdigit()

def is_valid_username(u: str) -> bool:
    return bool(re.fullmatch(r'@[A-Za-z0-9_]{5,}', u))

# Помощники
def refresh_username(cid: int, un: str):
    u = db.get_user_by_chat(cid)
    if u and u.username != un:
        u.username = un or u.username
        db.save_user(u)

def show_main_menu(cid: int):
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton("💸 Отправить", callback_data='send'),
        types.InlineKeyboardButton("💰 Запросить", callback_data='request')
    )
    kb.add(types.InlineKeyboardButton("⚙️ Настройки", callback_data='settings'))
    bot.send_message(cid, "Выберите действие:", reply_markup=kb)

# ===== Регистрация =====
@bot.message_handler(commands=['start'])
def cmd_start(msg: types.Message):
    cid = msg.chat.id
    awaiting_reg.add(cid)
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.add(types.KeyboardButton("Отправить контакт", request_contact=True))
    bot.send_message(
        cid,
        "Добро пожаловать! Укажите номер телефона:\nМожно нажать кнопку или ввести вручную.",
        reply_markup=kb
    )

@bot.message_handler(func=lambda m: m.chat.id in awaiting_reg,
                     content_types=['contact', 'text'])
def receive_phone(m: types.Message):
    cid = m.chat.id
    phone = m.contact.phone_number if m.content_type == 'contact' else m.text.strip()
    valid = is_valid_phone_contact(phone) if m.content_type == 'contact' else is_valid_phone_manual(phone)

    if not valid:
        return bot.send_message(cid, "❌ Неверный формат номера.", reply_markup=types.ReplyKeyboardRemove())

    if db.is_phone_taken_by_other(phone, cid):
        return bot.send_message(cid, "❌ Номер уже используется.", reply_markup=types.ReplyKeyboardRemove())

    reg_temp[cid] = phone
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton("Да, сохранить", callback_data='reg_yes'),
        types.InlineKeyboardButton("Нет, изменить", callback_data='reg_no')
    )
    bot.send_message(cid, f"Ваш счёт привязан к этому номеру телефона: {phone}?", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data in ('reg_yes','reg_no'))
def confirm_reg(call: types.CallbackQuery):
    cid = call.message.chat.id
    if call.data == 'reg_yes' and cid in reg_temp:
        phone = reg_temp.pop(cid)
        u = call.from_user
        name = u.first_name or ''
        if u.last_name:
            name += ' ' + u.last_name
        if phone.startswith("+7"):
            phone= "8" + phone[2:]
        elif phone.startswith("7"):
            phone= "8" + phone[1:]
        user = User(chat_id=cid, username=u.username or '', name=name, phone=phone,
    messenger_type='telegram' )
        db.save_user(user)
        registr_account_by_phone(phone, name)
        awaiting_reg.discard(cid)
        bot.send_message(cid, "✅ Регистрация завершена!", reply_markup=types.ReplyKeyboardRemove())
        show_main_menu(cid)

    elif call.data == 'reg_no':
        reg_temp.pop(cid, None)
        bot.send_message(cid, "Введите номер вручную (+7… или 8…):")
    bot.answer_callback_query(call.id)

# ===== Send Flow =====
@bot.callback_query_handler(func=lambda c: c.data == 'send')
def send_start(call: types.CallbackQuery):
    cid = call.message.chat.id
    refresh_username(cid, call.from_user.username or '')
    send_state[cid] = SendFlow(chat_id=cid)
    bot.send_message(cid, "Введите @username получателя:")
    bot.answer_callback_query(call.id)
@bot.message_handler(func=lambda m: m.chat.id in send_state)
def send_flow(m: types.Message):
    f = send_state[m.chat.id]
    cid, text = m.chat.id, m.text.strip()

    if f.step == 'recipient':
        if not is_valid_username(text):
            return bot.send_message(cid, "❌ Неверный @username.")
        f.recipient, f.step = text[1:], 'amount'
        return bot.send_message(cid, "Укажите сумму (>0, до 2 знаков):")

    if f.step == 'amount':
        try:
            amount_float = float(text)
            if amount_float <= 0:
                return bot.send_message(cid, "❌ Сумма должна быть больше 0.")
        except ValueError:
            return bot.send_message(cid, "❌ Неверный формат суммы.")

        f.amount, f.step = text, 'message'

        # СОЗДАЕМ КЛАВИАТУРУ С КНОПКАМИ ЦЕЛЕЙ
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True, row_width=2)
        kb.add(
            types.KeyboardButton("🍽️ За ресторан"),
            types.KeyboardButton("🚕 За такси"),
            types.KeyboardButton("🎁 На подарок"),
            types.KeyboardButton("💰 Возврат долга"),
            types.KeyboardButton("💸 На карманные расходы"),
            types.KeyboardButton("✏️ Другое...")
        )
        kb.add("Без сообщения")

        return bot.send_message(
            cid,
            "Выберите цель перевода или введите своё сообщение:",
            reply_markup=kb
        )

    if f.step == 'message':
        # Обрабатываем выбор из кнопок
        if text in ["🍽️ За ресторан", "🚕 За такси", "🎁 На подарок",
                   "💰 Возврат долга", "💸 На карманные расходы"]:
            f.details = text
        elif text == "✏️ Другое...":
            f.details = ""
            # Убираем клавиатуру и просим ввести сообщение вручную
            remove_kb = types.ReplyKeyboardRemove()
            bot.send_message(cid, "Введите ваше сообщение:", reply_markup=remove_kb)
            return  # Остаемся на том же шаге
        elif text == "Без сообщения":
            f.details = ''
        else:
            # Пользователь ввел свое сообщение
            f.details = text

        if len(f.details) > 200:
            return bot.send_message(cid, "❌ Сообщение слишком длинное.")

        f.step = 'confirm'
        kb = types.InlineKeyboardMarkup()
        kb.add(
            types.InlineKeyboardButton("✅ Подтвердить", callback_data='send_ok'),
            types.InlineKeyboardButton("✏️ Изменить",   callback_data='send_edit')
        )

        # Формируем сообщение подтверждения
        message_text = f"Проверьте данные:\nПолучатель: @{f.recipient}\nСумма: {f.amount} ₽"
        if f.details:
            message_text += f"\nСообщение: {f.details}"

        bot.send_message(cid, message_text, reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data in ('send_ok', 'send_edit'))
def send_confirm(call: types.CallbackQuery):
    cid = call.message.chat.id
    f = send_state.get(cid)
    if not f:
        return bot.answer_callback_query(call.id)

    if call.data == 'send_ok':
        dest = db.get_chat_by_username(f.recipient)
        if not dest:
            tmpl = (f"Привет! Зарегистрируйся в боте @{BOT_USERNAME} "
                    f"чтобы получить перевод на {f.amount} ₽.")
            bot.send_message(cid, "❌ Получатель не зарегестрирован в боте, перевод невозможен!\nОтправьте это сообщение @" + f.recipient,
                             reply_markup=types.ReplyKeyboardRemove())
            bot.send_message(cid, tmpl)
        else:
            try:
                send_transfer_warning(cid, f.recipient, f.amount, is_request=False)
                requester = db.get_user_by_chat(cid)
                payer_name = f"{requester.username}" if requester and requester.username else "Отправитель запроса"
                payer= [payer_name]
                link = f.generate_link()
                parsed_url = urlparse(link)
                query_params = parse_qs(parsed_url.query)
                link_id = int(query_params.get('id', [None])[0])
                db.addTransfer(
                    recipient=f.recipient,
                    payers=payer,
                    amount=f.amount,
                    details=f.details,
                    link_id=link_id
                )
                if f.details:
                    msg_text = (f"💸 Перевод на сумму {f.amount} ₽\n"
                                f"Для: @{f.recipient}\n"
                                f"Сообщение: {f.details}\n"
                                f"Ссылка на перевод: {link}")
                else:
                    msg_text = (f"💸 Перевод на сумму {f.amount} ₽\n"
                                f"Для: @{f.recipient}\n"
                                f"Ссылка на перевод: {link}")

                bot.send_message(cid, msg_text, reply_markup=types.ReplyKeyboardRemove())
                try:
                    # Отправляем локальное изображение с подписью
                    with open('advertisement.jpg', 'rb') as photo:
                        caption = "«Сделали, как для себя» Оформите дебетовую карту ВТБ прямо сейчас: https://www.vtb.ru/personal/karty/debetovye/"
                        bot.send_photo(cid, photo, caption=caption)
                except Exception as e:
                    print(f"Ошибка отправки изображения: {e}")
                    # Fallback на текстовое сообщение если изображение не найдено
                    bot.send_message(cid, "📢 Ваша реклама здесь! Свяжитесь с нами для размещения.")
            except Exception as e:
                bot.send_message(
                    cid,
                    f"❌ Ошибка при создании платежа:\n{str(e)}\n\n"
                    "Попробуйте позже или обратитесь в поддержку.",
                    reply_markup=types.ReplyKeyboardRemove()
                )

        send_state.pop(cid)
        show_main_menu(cid)
    else:  # edit
        send_state[cid] = SendFlow(chat_id=cid)
        bot.send_message(cid, "✏️ Введите @username получателя заново:",
                         reply_markup=types.ReplyKeyboardRemove())
    bot.answer_callback_query(call.id)

# ===== Request Flow =====
@bot.callback_query_handler(func=lambda c: c.data == 'request')
def req_start(call: types.CallbackQuery):
    cid = call.message.chat.id
    refresh_username(cid, call.from_user.username or '')
    request_state[cid] = RequestFlow(chat_id=cid)

    try:
        bot.answer_callback_query(call.id)
    except Exception as e:
        if "query is too old" in str(e) or "query ID is invalid" in str(e):
            print(f"Игнорируем устаревший callback query: {call.id}")
        else:
            raise

    # Создаем клавиатуру с кнопкой открытого сбора
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("📢 Создать открытый сбор", callback_data='open_collection'))

    bot.send_message(cid, "Введите @username плательщиков через пробел:", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data == 'open_collection')
def create_open_collection(call: types.CallbackQuery):
    cid = call.message.chat.id
    f = request_state.get(cid)

    if f:
        f.is_open_collection = True
        f.payers = []  # Пустой список для открытого сбора
        f.step = 'amount'

        bot.send_message(cid, "✅ Создан открытый сбор. Укажите сумму с каждого участника (>0):")

    bot.answer_callback_query(call.id)


@bot.message_handler(func=lambda m: m.chat.id in request_state)
def req_flow(m: types.Message):
    f = request_state[m.chat.id]
    cid, text = m.chat.id, m.text.strip()

    if f.step == 'payers':
        # Если это открытый сбор, пропускаем ввод плательщиков
        if f.is_open_collection:
            f.step = 'amount'
            return bot.send_message(cid, "Укажите сумму с каждого участника (>0):")

        users = [u[1:] for u in text.split() if is_valid_username(u)]
        if not users:
            return bot.send_message(cid, "❌ Некорректные @username.")
        f.payers, f.step = users, 'amount'
        return bot.send_message(cid, "Укажите сумму с каждого плательщика (>0):")

    if f.step == 'amount':
        try:
            amount_float = float(text)
            if amount_float <= 0:
                return bot.send_message(cid, "❌ Сумма должна быть больше 0.")
        except ValueError:
            return bot.send_message(cid, "❌ Неверный формат суммы.")

        f.amount, f.step = text, 'message'

        # СОЗДАЕМ КЛАВИАТУРУ С КНОПКАМИ ЦЕЛЕЙ ДЛЯ ЗАПРОСОВ
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True, row_width=2)
        kb.add(
            types.KeyboardButton("🍽️ За ресторан"),
            types.KeyboardButton("🚕 За такси"),
            types.KeyboardButton("🎁 На подарок"),
            types.KeyboardButton("💰 Возврат долга"),
            types.KeyboardButton("💸 На карманные расходы"),
            types.KeyboardButton("✏️ Другое...")
        )
        kb.add("Без сообщения")

        return bot.send_message(
            cid,
            "Выберите цель запроса или введите своё сообщение:",
            reply_markup=kb
        )

    if f.step == 'message':
        # Обрабатываем выбор из кнопок (такая же логика как в send_flow)
        if text in ["🍽️ За ресторан", "🚕 За такси", "🎁 На подарок",
                   "💰 Возврат долга", "💸 На карманные расходы"]:
            f.details = text
        elif text == "✏️ Другое...":
            f.details = ""
            remove_kb = types.ReplyKeyboardRemove()
            bot.send_message(cid, "Введите ваше сообщение:", reply_markup=remove_kb)
            return
        elif text == "Без сообщения":
            f.details = ''
        else:
            f.details = text

        if len(f.details) > 200:
            return bot.send_message(cid, "❌ Сообщение слишком длинное.")

        f.step = 'confirm'
        kb = types.InlineKeyboardMarkup()
        kb.add(
            types.InlineKeyboardButton("✅ Подтвердить", callback_data='req_ok'),
            types.InlineKeyboardButton("✏️ Изменить",   callback_data='req_edit')
        )

        # Формируем сообщение подтверждения в зависимости от типа сбора
        if f.is_open_collection:
            message_text = f"📢 Открытый сбор\nСумма с каждого: {f.amount} ₽"
        else:
            message_text = f"Плательщики: {', '.join('@'+u for u in f.payers)}\nСумма с каждого: {f.amount} ₽"

        if f.details:
            message_text += f"\nСообщение: {f.details}"

        bot.send_message(cid, f"Проверьте данные:\n{message_text}", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data in ('req_ok', 'req_edit'))
def req_confirm(call: types.CallbackQuery):
    cid = call.message.chat.id
    f = request_state.get(cid)
    if not f:
        return bot.answer_callback_query(call.id)

    if call.data == 'req_ok':
        requester = db.get_user_by_chat(cid)
        requester_name = f"{requester.username}" if requester and requester.username else "Отправитель запроса"

        # 🔴 ОБРАБОТКА ОТКРЫТЫХ СБОРОВ
        if f.is_open_collection:
            try:
                # Для открытых сборов создаем многоразовую ссылку
                disposable = False  # Многоразовая ссылка для открытых сборов
                link = f.generate_link(requester_name, disposable)

                parsed_url = urlparse(link)
                query_params = parse_qs(parsed_url.query)
                link_id = int(query_params.get('id', [None])[0])

                # Сохраняем в БД с пустым списком плательщиков
                db.addTransfer(
                    recipient=requester_name,
                    payers=[],  # 🔴 Пустой список для открытых сборов
                    amount=f.amount,
                    details=f.details,
                    link_id=link_id
                )

                # Показываем ссылку создателю
                if f.details:
                    msg_text = (f"📢 Открытый сбор создан!\n"
                               f"Сумма с каждого: {f.amount} ₽\n"
                               f"Сообщение: {f.details}\n"
                               f"Ссылка для перевода: {link}")
                else:
                    msg_text = (f"📢 Открытый сбор создан!\n"
                               f"Сумма с каждого: {f.amount} ₽\n"
                               f"Ссылка для перевода: {link}")

                bot.send_message(cid, msg_text, reply_markup=types.ReplyKeyboardRemove())
                try:
                    # Отправляем локальное изображение с подписью
                    with open('advertisement.jpg', 'rb') as photo:
                        caption = "«Сделали, как для себя» Оформите дебетовую карту ВТБ прямо сейчас: https://www.vtb.ru/personal/karty/debetovye/"
                        bot.send_photo(cid, photo, caption=caption)
                except Exception as e:
                    print(f"Ошибка отправки изображения: {e}")
                    # Fallback на текстовое сообщение если изображение не найдено
                    bot.send_message(cid, "📢 Ваша реклама здесь! Свяжитесь с нами для размещения.")
            except Exception as e:
                bot.send_message(
                    cid,
                    f"❌ Ошибка при создании открытого сбора:\n{str(e)}\n\n"
                    "Попробуйте позже или обратитесь в поддержку.",
                    reply_markup=types.ReplyKeyboardRemove()
                )

        else:
            # СУЩЕСТВУЮЩАЯ ЛОГИКА для обычных сборов
            for payer_username in f.payers:
                payer_chat_id = db.get_chat_by_username(payer_username)
                if payer_chat_id:
                    send_transfer_warning(payer_chat_id, requester_name, f.amount, is_request=True)

            sent, not_reg, errors = [], [], []
            disposable = checkDisposable(f.payers)
            link = f.generate_link(requester_name, disposable)

            parsed_url = urlparse(link)
            query_params = parse_qs(parsed_url.query)
            link_id = int(query_params.get('id', [None])[0])

            db.addTransfer(
                recipient=requester_name,
                payers=f.payers,
                amount=f.amount,
                details=f.details,
                link_id=link_id
            )

            for u in f.payers:
                chat_id = db.get_chat_by_username(u)
                if chat_id:
                    try:
                        if f.details:
                            bot.send_message(
                                chat_id,
                                f"💰 Запрос на {f.amount} ₽\n"
                                f"От: @{requester_name}\n"
                                f"Сообщение: {f.details}\n"
                                f"Ссылка для перевода: {link}"
                            )
                        else:
                            bot.send_message(
                                chat_id,
                                f"💰 Запрос на {f.amount} ₽\n"
                                f"От: @{requester_name}\n"
                                f"Ссылка для перевода: {link}"
                            )
                        sent.append(f"@{u}")
                    except Exception as e:
                        errors.append(f"@{u}: {str(e)}")
                else:
                    not_reg.append(f"@{u}")

            # Формируем отчет пользователю
            report = []
            if sent:
                report.append(f"✅ Отправлено: {', '.join(sent)}")
            if not_reg:
                if len(not_reg)==1:
                    tmpl = (f"\n\n❌ Данный отправитель не зарегистрирован в боте: {', '.join(not_reg)}\n"
                            f"Можете отправить ссылку лично\n"
                            f"Ссылка для перевода: {link}")
                    report.append(tmpl)
                else:
                    tmpl = (f"\n\n❌ Данные отправители не зарегистрирован в боте: {', '.join(not_reg)}\n"
                            f"Можете отправить ссылку лично\n"
                            f"Ссылка для перевода: {link}")
                    report.append(tmpl)
            if errors:
                report.append(f"\n\n⚠️ Ошибки: {'; '.join(errors)}")

            bot.send_message(
                cid,
                "\n".join(report),
                reply_markup=types.ReplyKeyboardRemove()
            )
            try:
                # Отправляем локальное изображение с подписью
                with open('advertisement.jpg', 'rb') as photo:
                    caption = "«Сделали, как для себя» Оформите дебетовую карту ВТБ прямо сейчас: https://www.vtb.ru"
                    bot.send_photo(cid, photo, caption=caption)
            except Exception as e:
                print(f"Ошибка отправки изображения: {e}")
                # Fallback на текстовое сообщение если изображение не найдено
                bot.send_message(cid, "📢 Ваша реклама здесь! Свяжитесь с нами для размещения.")
        request_state.pop(cid)
        show_main_menu(cid)

    else:  # edit
        request_state[cid] = RequestFlow(chat_id=cid)
        bot.send_message(cid, "✏️ Введите @username заново:",
                         reply_markup=types.ReplyKeyboardRemove())
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c: c.data == 'settings')
def settings_menu(call: types.CallbackQuery):
    cid = call.message.chat.id
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton("Изменить телефон", callback_data='set_phone'),
        types.InlineKeyboardButton("Удалить аккаунт", callback_data='delete_account')
    )
    kb.add(types.InlineKeyboardButton("Назад", callback_data='back_to_menu'))
    bot.send_message(cid, "⚙️ Настройки:", reply_markup=kb)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c: c.data == 'set_phone')
def settings_set_phone(call: types.CallbackQuery):
    cid = call.message.chat.id
    changing_phone.add(cid)
    bot.send_message(cid, "Введите новый номер телефона (+7XXXXXXXXXX или 8XXXXXXXXXX):")
    awaiting_reg.add(cid)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c: c.data == 'delete_account')
def settings_delete_account(call: types.CallbackQuery):
    cid = call.message.chat.id
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton("✅ Да, удалить", callback_data='del_yes'),
        types.InlineKeyboardButton("❌ Отмена", callback_data='del_no')
    )
    bot.send_message(cid, "Вы уверены, что хотите удалить аккаунт? Это действие необратимо.", reply_markup=kb)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c: c.data in ('del_yes','del_no'))
def settings_delete_confirm(call: types.CallbackQuery):
    cid = call.message.chat.id
    if call.data == 'del_yes':
        db.delete_user(cid)
        bot.send_message(cid, "✅ Ваш аккаунт удалён. Для повторной работы пройдите регистрацию снова.", reply_markup=types.ReplyKeyboardRemove())
        awaiting_reg.add(cid)
        cmd_start(call.message)
    else:
        settings_menu(call)
    call.answer()

@bot.callback_query_handler(func=lambda c: c.data == 'back_to_menu')
def back_to_main_menu(call: types.CallbackQuery):
    cid = call.message.chat.id
    show_main_menu(cid)
    bot.answer_callback_query(call.id)

if __name__ == '__main__':
    bot.infinity_polling()
