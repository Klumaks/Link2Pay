# vk_bot.py - ИСПРАВЛЕННАЯ ВЕРСИЯ (с прямым созданием аккаунта в opkc)
import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
import os
import re
from urllib.parse import urlparse, parse_qs
from dotenv import load_dotenv
import psycopg2

from database import db, User
from models import SendFlow, RequestFlow, registr_account_by_phone, checkDisposable

load_dotenv()

TOKEN = os.getenv('VK_BOT_TOKEN')
GROUP_ID = int(os.getenv('VK_GROUP_ID', 0))

if not TOKEN:
    raise ValueError("VK_BOT_TOKEN не найден в .env файле")

# Состояния пользователей
reg_temp = {}
awaiting_reg = set()
send_state = {}
request_state = {}
changing_phone = set()

# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========

def is_valid_phone_manual(p):
    """Проверка формата телефона"""
    cleaned = re.sub(r'[^\d]', '', p)

    if len(cleaned) == 11 and (cleaned.startswith('8') or cleaned.startswith('7')):
        return True
    if len(cleaned) == 12 and cleaned.startswith('7'):
        return True

    return False

def normalize_phone(phone):
    """Нормализует номер телефона к формату 8XXXXXXXXXX"""
    cleaned = re.sub(r'[^\d]', '', phone)

    if cleaned.startswith('7'):
        return '8' + cleaned[1:]
    if cleaned.startswith('8'):
        return cleaned

    return cleaned

def normalize_username(username):
    """Нормализует username - убирает @ и приводит к нижнему регистру"""
    return username.lstrip('@').strip().lower()

def is_valid_username(u):
    """Проверяет формат username"""
    username = normalize_username(u)
    # VK username может быть: screen_name, id123456789
    if username.startswith('id') and username[2:].isdigit():
        return True
    # Разрешаем буквы, цифры, подчеркивание, дефис, точку (как в VK)
    # Минимум 2 символа
    return bool(re.fullmatch(r'[a-z0-9_.-]{2,}', username))
    """Проверяет формат username"""
    username = normalize_username(u)
    if username.startswith('id') and username[2:].isdigit():
        return True
    return bool(re.fullmatch(r'[a-z0-9_]{2,}', username))

def get_user_screen_name(vk, user_id):
    """Получает screen_name пользователя VK"""
    try:
        user_info = vk.users.get(user_ids=user_id, fields=['screen_name'])
        if user_info:
            u = user_info[0]
            if u.get('screen_name'):
                return u['screen_name'].lower()
            return f"id{user_id}"
    except Exception as e:
        print(f"Ошибка получения screen_name: {e}")
    return f"id{user_id}"

def refresh_username(vk, vk_id, vk_username):
    """Обновляет username в БД"""
    current_username = get_user_screen_name(vk, vk_id)
    u = db.get_user_by_chat(vk_id)
    if u and u.username != current_username:
        u.username = current_username
        db.save_user(u)
        print(f"🔄 Обновлен username для {vk_id}: {u.username} -> {current_username}")

# ========== НОВАЯ ФУНКЦИЯ: ПРЯМОЕ СОЗДАНИЕ АККАУНТА В opkc ==========

def create_account_in_opkc(phone, name):
    """Создает аккаунт напрямую в базе opkc (как в Telegram боте)"""
    try:
        conn = psycopg2.connect(
            dbname='opkc',
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASS', 'z8w(XRG?e6f4Fqn90O-'),
            host=os.getenv('DB_HOST', 'localhost'),
            port=os.getenv('DB_PORT', '5432')
        )

        with conn.cursor() as cur:
            # Проверяем, существует ли уже аккаунт
            cur.execute("SELECT account FROM account WHERE phone_number = %s", (phone,))
            existing = cur.fetchone()

            if existing:
                print(f"✅ Аккаунт уже существует: {existing[0]}")
                return existing[0]

            # Генерируем новый 20-значный счет
            import random
            new_account = ''.join(str(random.randint(0, 9)) for _ in range(20))

            # Сохраняем в базу
            cur.execute("""
                INSERT INTO account (phone_number, pam, bank, account)
                VALUES (%s, %s, %s, %s)
                RETURNING account
            """, (phone, name, "", new_account))

            saved_account = cur.fetchone()[0]
            conn.commit()

            print(f"✅ Создан аккаунт в opkc:")
            print(f"   Телефон: {phone}")
            print(f"   Имя: {name}")
            print(f"   Счет: {saved_account}")

            return saved_account

    except Exception as e:
        print(f"❌ Ошибка создания аккаунта в opkc: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        if conn:
            conn.close()

# ========== КЛАВИАТУРЫ ==========

def create_main_keyboard():
    keyboard = VkKeyboard(one_time=False)
    keyboard.add_button('💸 Отправить', color=VkKeyboardColor.POSITIVE)
    keyboard.add_button('💰 Запросить', color=VkKeyboardColor.POSITIVE)
    keyboard.add_line()
    keyboard.add_button('⚙️ Настройки', color=VkKeyboardColor.PRIMARY)
    return keyboard.get_keyboard()

def create_back_keyboard():
    keyboard = VkKeyboard(one_time=False)
    keyboard.add_button('🔙 Назад', color=VkKeyboardColor.SECONDARY)
    return keyboard.get_keyboard()

def create_confirm_keyboard():
    keyboard = VkKeyboard(one_time=False)
    keyboard.add_button('✅ Подтвердить', color=VkKeyboardColor.POSITIVE)
    keyboard.add_button('✏️ Изменить', color=VkKeyboardColor.NEGATIVE)
    return keyboard.get_keyboard()

def create_reg_confirm_keyboard():
    keyboard = VkKeyboard(one_time=False)
    keyboard.add_button('✅ Да, сохранить', color=VkKeyboardColor.POSITIVE)
    keyboard.add_button('✏️ Нет, изменить', color=VkKeyboardColor.NEGATIVE)
    return keyboard.get_keyboard()

def create_message_keyboard():
    keyboard = VkKeyboard(one_time=True)
    keyboard.add_button('🍽️ За ресторан', color=VkKeyboardColor.PRIMARY)
    keyboard.add_button('🚕 За такси', color=VkKeyboardColor.PRIMARY)
    keyboard.add_line()
    keyboard.add_button('🎁 На подарок', color=VkKeyboardColor.PRIMARY)
    keyboard.add_button('💰 Возврат долга', color=VkKeyboardColor.PRIMARY)
    keyboard.add_line()
    keyboard.add_button('💸 На карманные расходы', color=VkKeyboardColor.PRIMARY)
    keyboard.add_button('✏️ Другое...', color=VkKeyboardColor.SECONDARY)
    keyboard.add_line()
    keyboard.add_button('Без сообщения', color=VkKeyboardColor.SECONDARY)
    return keyboard.get_keyboard()

def create_settings_keyboard():
    keyboard = VkKeyboard(one_time=False)
    keyboard.add_button('Изменить телефон', color=VkKeyboardColor.PRIMARY)
    keyboard.add_button('Удалить аккаунт', color=VkKeyboardColor.NEGATIVE)
    keyboard.add_line()
    keyboard.add_button('🔙 Назад', color=VkKeyboardColor.SECONDARY)
    return keyboard.get_keyboard()

def create_delete_keyboard():
    keyboard = VkKeyboard(one_time=False)
    keyboard.add_button('✅ Да, удалить', color=VkKeyboardColor.NEGATIVE)
    keyboard.add_button('❌ Отмена', color=VkKeyboardColor.PRIMARY)
    return keyboard.get_keyboard()

def create_open_collection_keyboard():
    keyboard = VkKeyboard(one_time=False)
    keyboard.add_button('📢 Создать открытый сбор', color=VkKeyboardColor.PRIMARY)
    return keyboard.get_keyboard()

def send_message(vk, peer_id, message, keyboard=None):
    try:
        vk.messages.send(
            peer_id=peer_id,
            message=message,
            random_id=0,
            keyboard=keyboard if keyboard else None
        )
    except Exception as e:
        print(f"Ошибка отправки: {e}")

def show_main_menu(vk, peer_id):
    send_message(vk, peer_id, "Выберите действие:", create_main_keyboard())

# ========== РЕГИСТРАЦИЯ ==========

def handle_start(vk, peer_id):
    awaiting_reg.add(peer_id)
    send_message(vk, peer_id,
        "Добро пожаловать! Укажите номер телефона:\n"
        "Можно ввести вручную в формате +7XXXXXXXXXX или 8XXXXXXXXXX:")

def handle_phone_input(vk, peer_id, text):
    phone = text.strip()

    if not is_valid_phone_manual(phone):
        send_message(vk, peer_id, "❌ Неверный формат номера.\n\nВведите номер в формате +7XXXXXXXXXX или 8XXXXXXXXXX:")
        return

    if db.is_phone_taken_by_other(phone, peer_id):
        send_message(vk, peer_id, "❌ Номер уже используется.")
        return

    reg_temp[peer_id] = phone

    display_number = phone
    if phone.startswith('8'):
        display_number = '+7' + phone[1:]

    send_message(vk, peer_id, f"Ваш счёт привязан к этому номеру телефона: {display_number}?",
                 create_reg_confirm_keyboard())

def handle_confirm_reg(vk, peer_id, text):
    if text == "✅ Да, сохранить" and peer_id in reg_temp:
        phone = reg_temp.pop(peer_id)

        # Получаем информацию о пользователе VK
        try:
            user_info = vk.users.get(user_ids=peer_id, fields=['screen_name', 'first_name', 'last_name'])
            u = user_info[0]
            name = u['first_name'] or ''
            if u.get('last_name'):
                name += ' ' + u['last_name']

            screen_name = u.get('screen_name')
            if screen_name:
                vk_username = screen_name.lower()
                print(f"📱 Найден screen_name: {vk_username}")
            else:
                vk_username = f"id{peer_id}"
                print(f"📱 Нет screen_name, используем id: {vk_username}")

        except Exception as e:
            print(f"Ошибка получения данных: {e}")
            name = f"User_{peer_id}"
            vk_username = f"id{peer_id}"

        phone = normalize_phone(phone)

        # Сохраняем пользователя в link2pay
        user = User(chat_id=peer_id, username=vk_username, name=name, phone=phone,
    messenger_type='vk')
        db.save_user(user)

        print(f"✅ Зарегистрирован пользователь в link2pay:")
        print(f"   Chat ID: {peer_id}")
        print(f"   Username: {vk_username}")
        print(f"   Name: {name}")
        print(f"   Phone: {phone}")

        # 🔴 СОЗДАЕМ АККАУНТ В opkc (как в Telegram боте)
        print(f"🔍 Создаем аккаунт в opkc для {phone}...")
        create_account_in_opkc(phone, name)

        awaiting_reg.discard(peer_id)

        send_message(vk, peer_id, "✅ Регистрация завершена!")
        show_main_menu(vk, peer_id)

    elif text == "✏️ Нет, изменить":
        reg_temp.pop(peer_id, None)
        send_message(vk, peer_id, "Введите номер вручную (+7… или 8…):")

# ========== ОТПРАВКА ПЕРЕВОДА ==========
# ... (остальной код без изменений, функции handle_send_start, handle_send_flow, handle_send_confirm и т.д.)

def handle_send_start(vk, peer_id):
    refresh_username(vk, peer_id, f"id{peer_id}")
    send_state[peer_id] = SendFlow(chat_id=peer_id, step='recipient')
    send_message(vk, peer_id, "Введите @username получателя (например, @durov или durov):")

def handle_send_flow(vk, peer_id, text):
    f = send_state.get(peer_id)
    if not f:
        return

    if f.step == 'recipient':
        username = normalize_username(text)

        if not is_valid_username(username):
            send_message(vk, peer_id, "❌ Неверный @username. Используйте формат: @durov или durov")
            return

        print(f"🔍 Ищем пользователя: '{username}'")

        recipient_user = db.get_user_by_username(username)

        if not recipient_user and username.startswith('id'):
            try:
                chat_id = int(username[2:])
                recipient_user = db.get_user_by_chat(chat_id)
                if recipient_user:
                    username = recipient_user.username
                    print(f"✅ Нашли по ID: {username}")
            except:
                pass

        if not recipient_user:
            send_message(vk, peer_id,
                f"❌ Пользователь @{username} не зарегистрирован в боте.\n\n"
                f"Попросите его написать 'Начать' для регистрации.")
            send_state.pop(peer_id)
            show_main_menu(vk, peer_id)
            return

        f.recipient = username
        f.step = 'amount'
        send_message(vk, peer_id, f"Получатель: @{f.recipient}\nУкажите сумму (>0, до 2 знаков):")

    elif f.step == 'amount':
        try:
            amount_float = float(text.replace(',', '.'))
            if amount_float <= 0:
                send_message(vk, peer_id, "❌ Сумма должна быть больше 0.")
                return
        except ValueError:
            send_message(vk, peer_id, "❌ Неверный формат суммы.")
            return

        f.amount = text
        f.step = 'message'
        send_message(vk, peer_id, "Выберите цель перевода или введите своё сообщение:",
                     create_message_keyboard())

    elif f.step == 'message':
        if text in ["🍽️ За ресторан", "🚕 За такси", "🎁 На подарок",
                   "💰 Возврат долга", "💸 На карманные расходы"]:
            f.details = text
        elif text == "✏️ Другое...":
            f.details = ""
            send_message(vk, peer_id, "Введите ваше сообщение:", create_back_keyboard())
            return
        elif text == "Без сообщения":
            f.details = ''
        elif text == "🔙 Назад":
            send_state.pop(peer_id)
            show_main_menu(vk, peer_id)
            return
        else:
            f.details = text

        if len(f.details) > 200:
            send_message(vk, peer_id, "❌ Сообщение слишком длинное.")
            return

        f.step = 'confirm'

        message_text = f"Проверьте данные:\nПолучатель: @{f.recipient}\nСумма: {f.amount} ₽"
        if f.details:
            message_text += f"\nСообщение: {f.details}"

        send_message(vk, peer_id, message_text, create_confirm_keyboard())

def handle_send_confirm(vk, peer_id, text):
    f = send_state.get(peer_id)
    if not f:
        return

    if text == "✅ Подтвердить":
        try:
            requester = db.get_user_by_chat(peer_id)
            if not requester:
                send_message(vk, peer_id, "❌ Ошибка: вы не зарегистрированы!")
                send_state.pop(peer_id)
                show_main_menu(vk, peer_id)
                return

            payer_name = requester.username
            payer = [payer_name]

            print(f"📤 Создаем перевод от {payer_name} для @{f.recipient}")

            # Проверяем, есть ли аккаунт у получателя в opkc
            recipient_user = db.get_user_by_username(f.recipient)
            if recipient_user:
                create_account_in_opkc(recipient_user.phone, recipient_user.name)

            link = f.generate_link()
            print(f"🔗 Ссылка: {link}")

            parsed_url = urlparse(link)
            query_params = parse_qs(parsed_url.query)
            link_id = int(query_params.get('id', [None])[0])

            transfer_id = db.addTransfer(
                recipient=f.recipient,
                payers=payer,
                amount=f.amount,
                details=f.details,
                link_id=link_id
            )
            print(f"💾 Перевод сохранен, ID: {transfer_id}")

            # Отправляем ссылку ТОЛЬКО отправителю
            if f.details:
                msg_text = (f"💸 Перевод на сумму {f.amount} ₽\n"
                           f"Для: @{f.recipient}\n"
                           f"Сообщение: {f.details}\n\n"
                           f"🔗 Ссылка для перевода: {link}")
            else:
                msg_text = (f"💸 Перевод на сумму {f.amount} ₽\n"
                           f"Для: @{f.recipient}\n\n"
                           f"🔗 Ссылка для перевода: {link}")

            send_message(vk, peer_id, msg_text)

            # 🔴 УБИРАЕМ отправку уведомления получателю!
            # Получатель НЕ должен получать ссылку до оплаты
            # recipient_chat_id = db.get_chat_by_username(f.recipient)
            # if recipient_chat_id:
            #     notification = f"💰 Вам перевод на сумму {f.amount} ₽\nОт: @{payer_name}\n\n🔗 Ссылка для перевода: {link}"
            #     send_message(vk, recipient_chat_id, notification)

            send_message(vk, peer_id, "✅ Перевод создан успешно!")

        except Exception as e:
            print(f"❌ Ошибка: {e}")
            import traceback
            traceback.print_exc()
            send_message(vk, peer_id, f"❌ Ошибка при создании перевода:\n{str(e)}")

        send_state.pop(peer_id)
        show_main_menu(vk, peer_id)

    elif text == "✏️ Изменить":
        send_state[peer_id] = SendFlow(chat_id=peer_id, step='recipient')
        send_message(vk, peer_id, "✏️ Введите @username получателя заново:",
                     create_back_keyboard())
# ========== ЗАПРОС ПЕРЕВОДА ==========
# ... (код для запросов остается без изменений)

def handle_request_start(vk, peer_id):
    refresh_username(vk, peer_id, f"id{peer_id}")
    request_state[peer_id] = RequestFlow(chat_id=peer_id, step='payers')
    send_message(vk, peer_id,
        "Введите @username плательщиков через пробел:\n\n"
        "Пример: @user1 @user2 @user3\n\n"
        "Или нажмите кнопку для создания открытого сбора:",
        create_open_collection_keyboard())

def handle_open_collection(vk, peer_id):
    f = request_state.get(peer_id)
    if f:
        f.is_open_collection = True
        f.payers = []
        f.step = 'amount'
        send_message(vk, peer_id, "✅ Создан открытый сбор. Укажите сумму с каждого участника (>0):")

def handle_request_flow(vk, peer_id, text):
    f = request_state.get(peer_id)
    if not f:
        return

    if f.step == 'payers':
        if f.is_open_collection:
            f.step = 'amount'
            send_message(vk, peer_id, "Укажите сумму с каждого участника (>0):")
            return

        users = []
        for u in text.split():
            username = normalize_username(u)
            if is_valid_username(username):
                user = db.get_user_by_username(username)
                if user:
                    users.append(username)
                else:
                    send_message(vk, peer_id, f"⚠️ Пользователь @{username} не зарегистрирован в боте")
            else:
                send_message(vk, peer_id, f"❌ Неверный формат: {u}")

        if not users:
            send_message(vk, peer_id, "❌ Нет зарегистрированных плательщиков.")
            return

        f.payers = users
        f.step = 'amount'
        send_message(vk, peer_id, f"Плательщики: {', '.join('@'+u for u in f.payers)}\nУкажите сумму с каждого (>0):")

    elif f.step == 'amount':
        try:
            amount_float = float(text.replace(',', '.'))
            if amount_float <= 0:
                send_message(vk, peer_id, "❌ Сумма должна быть больше 0.")
                return
        except ValueError:
            send_message(vk, peer_id, "❌ Неверный формат суммы.")
            return

        f.amount = text
        f.step = 'message'
        send_message(vk, peer_id, "Выберите цель запроса или введите своё сообщение:",
                     create_message_keyboard())

    elif f.step == 'message':
        if text in ["🍽️ За ресторан", "🚕 За такси", "🎁 На подарок",
                   "💰 Возврат долга", "💸 На карманные расходы"]:
            f.details = text
        elif text == "✏️ Другое...":
            f.details = ""
            send_message(vk, peer_id, "Введите ваше сообщение:", create_back_keyboard())
            return
        elif text == "Без сообщения":
            f.details = ''
        elif text == "🔙 Назад":
            request_state.pop(peer_id)
            show_main_menu(vk, peer_id)
            return
        else:
            f.details = text

        if len(f.details) > 200:
            send_message(vk, peer_id, "❌ Сообщение слишком длинное.")
            return

        f.step = 'confirm'

        if f.is_open_collection:
            message_text = f"📢 Открытый сбор\nСумма с каждого: {f.amount} ₽"
        else:
            message_text = f"Плательщики: {', '.join('@'+u for u in f.payers)}\nСумма с каждого: {f.amount} ₽"

        if f.details:
            message_text += f"\nСообщение: {f.details}"

        send_message(vk, peer_id, f"Проверьте данные:\n{message_text}", create_confirm_keyboard())

def handle_request_confirm(vk, peer_id, text):
    f = request_state.get(peer_id)
    if not f:
        return

    if text == "✅ Подтвердить":
        requester = db.get_user_by_chat(peer_id)
        if not requester:
            send_message(vk, peer_id, "❌ Ошибка: вы не зарегистрированы!")
            request_state.pop(peer_id)
            show_main_menu(vk, peer_id)
            return

        requester_name = requester.username

        if f.is_open_collection:
            try:
                # Создаем аккаунт для создателя сбора если нет
                create_account_in_opkc(requester.phone, requester.name)

                link = f.generate_link(requester_name, False)
                print(f"🔗 Ссылка открытого сбора: {link}")

                parsed_url = urlparse(link)
                query_params = parse_qs(parsed_url.query)
                link_id = int(query_params.get('id', [None])[0])

                db.addTransfer(
                    recipient=requester_name,
                    payers=[],
                    amount=f.amount,
                    details=f.details,
                    link_id=link_id
                )

                if f.details:
                    msg_text = (f"📢 Открытый сбор создан!\n"
                               f"💰 Сумма с каждого: {f.amount} ₽\n"
                               f"📝 Сообщение: {f.details}\n\n"
                               f"🔗 Ссылка для перевода: {link}")
                else:
                    msg_text = (f"📢 Открытый сбор создан!\n"
                               f"💰 Сумма с каждого: {f.amount} ₽\n\n"
                               f"🔗 Ссылка для перевода: {link}")

                send_message(vk, peer_id, msg_text)

            except Exception as e:
                send_message(vk, peer_id, f"❌ Ошибка: {str(e)}")

        else:
            try:
                # Создаем аккаунты для всех плательщиков если нет
                for u in f.payers:
                    user = db.get_user_by_username(u)
                    if user:
                        create_account_in_opkc(user.phone, user.name)

                disposable = checkDisposable(f.payers)
                link = f.generate_link(requester_name, disposable)
                print(f"🔗 Ссылка сбора: {link}")

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

                sent = []
                not_reg = []

                for u in f.payers:
                    chat_id = db.get_chat_by_username(u)
                    if chat_id:
                        try:
                            if f.details:
                                send_message(vk, chat_id,
                                    f"💰 Запрос на {f.amount} ₽\n"
                                    f"👤 От: @{requester_name}\n"
                                    f"📝 Сообщение: {f.details}\n\n"
                                    f"🔗 Ссылка для перевода: {link}")
                            else:
                                send_message(vk, chat_id,
                                    f"💰 Запрос на {f.amount} ₽\n"
                                    f"👤 От: @{requester_name}\n\n"
                                    f"🔗 Ссылка для перевода: {link}")
                            sent.append(f"@{u}")
                        except Exception as e:
                            print(f"Ошибка отправки {u}: {e}")
                    else:
                        not_reg.append(f"@{u}")

                report = []
                if sent:
                    report.append(f"✅ Отправлено: {', '.join(sent)}")
                if not_reg:
                    report.append(f"\n❌ Не зарегистрированы: {', '.join(not_reg)}")
                    report.append(f"🔗 Ссылка: {link}")

                send_message(vk, peer_id, "\n".join(report))

            except Exception as e:
                send_message(vk, peer_id, f"❌ Ошибка: {str(e)}")

        request_state.pop(peer_id)
        show_main_menu(vk, peer_id)

    elif text == "✏️ Изменить":
        request_state[peer_id] = RequestFlow(chat_id=peer_id, step='payers')
        send_message(vk, peer_id, "✏️ Введите @username заново:", create_back_keyboard())

# ========== НАСТРОЙКИ ==========

def handle_settings(vk, peer_id):
    send_message(vk, peer_id, "⚙️ Настройки:", create_settings_keyboard())

def handle_change_phone(vk, peer_id):
    changing_phone.add(peer_id)
    awaiting_reg.add(peer_id)
    send_message(vk, peer_id, "Введите новый номер телефона (+7XXXXXXXXXX или 8XXXXXXXXXX):")

def handle_delete_account(vk, peer_id):
    send_message(vk, peer_id, "Вы уверены, что хотите удалить аккаунт? Это действие необратимо.",
                 create_delete_keyboard())

def handle_delete_confirm(vk, peer_id, text):
    if text == "✅ Да, удалить":
        db.delete_user(peer_id)
        send_message(vk, peer_id, "✅ Ваш аккаунт удалён. Для повторной работы пройдите регистрацию снова.")
        awaiting_reg.add(peer_id)
        handle_start(vk, peer_id)
    else:
        handle_settings(vk, peer_id)

def handle_back_to_menu(vk, peer_id):
    show_main_menu(vk, peer_id)

# ========== ГЛАВНЫЙ ЦИКЛ ==========

def main():
    print("=" * 60)
    print("🚀 VK БОТ ЗАПУЩЕН")
    print("=" * 60)
    print(f"📍 ID группы: {GROUP_ID}")
    print("💬 Напишите 'Начать' для регистрации")
    print("=" * 60)

    try:
        vk_session = vk_api.VkApi(token=TOKEN)
        vk = vk_session.get_api()
        longpoll = VkBotLongPoll(vk_session, GROUP_ID, wait=25)

        print("✅ Бот успешно подключен")
        print("📨 Ожидание сообщений...\n")

        for event in longpoll.listen():
            if event.type == VkBotEventType.MESSAGE_NEW:
                msg = event.message
                peer_id = msg['peer_id']
                text = msg.get('text', '').strip()

                if not text:
                    continue

                print(f"📨 Получено: '{text}' от {peer_id}")

                user = db.get_user_by_chat(peer_id)

                if text == "Начать":
                    if user:
                        show_main_menu(vk, peer_id)
                    else:
                        handle_start(vk, peer_id)

                elif text in ["✅ Да, сохранить", "✏️ Нет, изменить"] and peer_id in reg_temp:
                    handle_confirm_reg(vk, peer_id, text)

                elif peer_id in awaiting_reg:
                    handle_phone_input(vk, peer_id, text)

                elif user is None:
                    send_message(vk, peer_id,
                        "❌ Вы не зарегистрированы! Напишите 'Начать' для регистрации.")

                elif text == "💸 Отправить":
                    handle_send_start(vk, peer_id)

                elif text == "💰 Запросить":
                    handle_request_start(vk, peer_id)

                elif text == "📢 Создать открытый сбор":
                    handle_open_collection(vk, peer_id)

                elif text in ["✅ Подтвердить", "✏️ Изменить"]:
                    if peer_id in send_state:
                        handle_send_confirm(vk, peer_id, text)
                    elif peer_id in request_state:
                        handle_request_confirm(vk, peer_id, text)

                elif text == "⚙️ Настройки":
                    handle_settings(vk, peer_id)

                elif text == "Изменить телефон":
                    handle_change_phone(vk, peer_id)

                elif text == "Удалить аккаунт":
                    handle_delete_account(vk, peer_id)

                elif text in ["✅ Да, удалить", "❌ Отмена"]:
                    handle_delete_confirm(vk, peer_id, text)

                elif text == "🔙 Назад":
                    handle_back_to_menu(vk, peer_id)

                elif peer_id in send_state:
                    handle_send_flow(vk, peer_id, text)

                elif peer_id in request_state:
                    handle_request_flow(vk, peer_id, text)

                else:
                    send_message(vk, peer_id,
                        "Неизвестная команда.\n\n"
                        "Доступные действия:\n"
                        "• Начать - регистрация\n"
                        "• 💸 Отправить - перевод\n"
                        "• 💰 Запросить - запрос\n"
                        "• ⚙️ Настройки - настройки")

    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
