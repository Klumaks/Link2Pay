from models import get_transfer_by_link_id_from_link_db, update_payment_progress, get_payment_progress, get_transfer_id_by_link_id
import traceback
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, constr
from fastapi.middleware.cors import CORSMiddleware
import psycopg2
from psycopg2 import sql
from typing import Optional
import random
import logging
import requests
import os
from dotenv import load_dotenv
import vk_api  # Добавить в импорты

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

def send_telegram_notification(chat_id: int, message: str):
    """Отправляет уведомление через Telegram Bot API"""
    try:
        bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not bot_token:
            logger.error("TELEGRAM_BOT_TOKEN не найден в переменных окружения")
            return False

        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

        payload = {
            'chat_id': chat_id,
            'text': message,
            'parse_mode': 'HTML'
        }

        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        logger.info(f"Уведомление отправлено в chat_id: {chat_id}")
        return True
    except Exception as e:
        logger.error(f"Ошибка отправки Telegram уведомления: {str(e)}")
        return False

def send_vk_notification(chat_id: int, message: str):
    """Отправляет уведомление через VK Bot API"""
    try:
        vk_token = os.getenv('VK_BOT_TOKEN')
        if not vk_token:
            logger.error("VK_BOT_TOKEN не найден")
            return False

        import vk_api
        vk_session = vk_api.VkApi(token=vk_token)
        vk = vk_session.get_api()

        vk.messages.send(
            peer_id=chat_id,
            message=message,
            random_id=0
        )
        logger.info(f"VK уведомление отправлено в chat_id: {chat_id}")
        return True
    except Exception as e:
        logger.error(f"Ошибка отправки VK уведомления: {str(e)}")
        return False
def format_notification_text(transfer_data: dict, amount: str, message: str, telegram_tag: str = None) -> str:
    """Форматирует текст уведомления"""
    payers_str = transfer_data.get('payers', '')

    if telegram_tag:
        return f"💸 Вам перевод {amount} ₽\nОт: {telegram_tag}"
    elif payers_str:
        return f"💸 Вам перевод {amount} ₽\nОт: @{payers_str}"
    else:
        return f"💸 Вам перевод {amount} ₽"

def send_transfer_notifications(transfer_data: dict, amount: str, message: str, telegram_tag: str = None, bank: str = None):
    """Отправляет уведомления о переводе с прогрессом"""
    try:
        recipient_username = transfer_data.get('recipient')
        recipient_chat_id = get_chat_by_username(recipient_username)

        if recipient_chat_id:
            notification_text = format_notification_text(transfer_data, amount, message, telegram_tag)

            from database import db
            recipient_user = db.get_user_by_chat(recipient_chat_id)

            if recipient_user:
                # 🔴 ИСПОЛЬЗУЕМ messenger_type для определения куда отправлять
                if recipient_user.messenger_type == 'vk':
                    send_vk_notification(recipient_chat_id, notification_text)
                else:
                    send_telegram_notification(recipient_chat_id, notification_text)
            else:
                # fallback: пробуем оба
                send_telegram_notification(recipient_chat_id, notification_text)
                send_vk_notification(recipient_chat_id, notification_text)

            logger.info(f"Уведомление отправлено получателю {recipient_username}")

        # Отправляем уведомление тому, кто оплатил
        if telegram_tag:
            payer_tag = telegram_tag.lstrip('@')
            payer_chat_id = get_chat_by_username(payer_tag)
            if payer_chat_id:
                success_text = f"✅ Перевод @{recipient_username} успешен!"

                from database import db
                payer_user = db.get_user_by_chat(payer_chat_id)

                if payer_user and payer_user.messenger_type == 'vk':
                    send_vk_notification(payer_chat_id, success_text)
                else:
                    send_telegram_notification(payer_chat_id, success_text)

                logger.info(f"Уведомление отправлено отправителю {payer_tag}")

    except Exception as e:
        logger.error(f"Ошибка отправки уведомлений: {str(e)}")
        import traceback
        traceback.print_exc()
# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class RegistrationRequest(BaseModel):
    phone_number: str
    pam: str

class PhoneRequest(BaseModel):
    phone: constr(pattern=r"^(\+7|8)\d{10}$")

class CreateLinkRequest(BaseModel):
    account_recipient: constr(pattern=r"^\d{20}$")
    amount: int
    bank_recipient: str
    pay_message: Optional[constr(max_length=140)] = None
    additionally: Optional[str] = None
    disposable: bool

class LinkDataResponse(BaseModel):
    account_recipient: str
    amount: int
    bank_recipient: str
    pay_message: Optional[str]
    additionally: Optional[str]
    pam: str
    phone_number: str
    status: bool

class TransferResponse(BaseModel):
    recipient: str
    payers: Optional[str]
    ammount: str
    details: Optional[str]

# APINIKITKA.py (исправленная часть)

def connect_to_db():
    try:
        conn = psycopg2.connect(
            dbname='opkc',
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASS', 'password'),
            host=os.getenv('DB_HOST', 'localhost'),
            port=os.getenv('DB_PORT', '5432')
        )
        return conn
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database connection error: {str(e)}")

def connect_to_db_link():
    try:
        conn = psycopg2.connect(
            dbname="link2pay",
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASS', 'password'),
            host=os.getenv('DB_HOST', 'localhost'),
            port=os.getenv('DB_PORT', '5432')
        )
        return conn
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database connection error: {str(e)}")
def generate_random_account() -> str:
    """Генерация валидного 20-значного номера счета"""
    return ''.join(str(random.randint(0, 9)) for _ in range(20))

class LogData(BaseModel):
    link_id: int

@app.post("/log")
async def handle_log(data: LogData):
    """Обработчик логов для уведомлений о переводах"""
    try:
        link_id = str(data.link_id)

        # Получаем информацию о переводе
        transfer_data = get_transfer_by_link(link_id)
        if isinstance(transfer_data, TransferResponse):
            transfer_data = transfer_data.dict()

        # Получаем chat_id получателя
        recipient_username = transfer_data.get('recipient')
        cid_rec = get_chat_by_username(recipient_username)

        # Получаем chat_id отправителя (если один)
        payers = transfer_data.get('payers', '')
        if payers and payers.count(', ') == 0:
            cid_prs = get_chat_by_username(payers)
        else:
            cid_prs = None

        # Отправляем уведомление получателю
        if cid_rec:
            message_parts = []
            message_parts.append(f"💸 Вам перевод {transfer_data.get('ammount')} ₽")

            if payers and cid_prs:
                message_parts.append(f"От: @{payers}")

            details = transfer_data.get('details')
            if details:
                message_parts.append(f"Сообщение: {details}")

            bot_message = "\n".join(message_parts)

            # Здесь нужно отправить сообщение ботом - для этого потребуется интеграция
            # Пока просто логируем
            logger.info(f"Уведомление для {cid_rec}: {bot_message}")

        # Отправляем уведомление отправителю
        if cid_prs:
            success_msg = f"✅ Перевод @{recipient_username} успешен!"
            logger.info(f"Уведомление для {cid_prs}: {success_msg}")

        return {"status": "success"}

    except Exception as e:
        logger.error(f"Ошибка в обработчике логов: {str(e)}")
        return {"status": "error", "message": str(e)}

def get_chat_by_username(username: str) -> Optional[int]:
    """Получает chat_id по username из базы данных"""
    conn = None
    try:
        conn = connect_to_db_link()
        with conn.cursor() as cursor:
            cursor.execute("SELECT chat_id FROM users WHERE username = %s", (username,))
            result = cursor.fetchone()
            return result[0] if result else None
    except Exception as e:
        logger.error(f"Ошибка при получении chat_id: {str(e)}")
        return None
    finally:
        if conn:
            conn.close()

@app.post("/regist_account")
async def regist_account(request: RegistrationRequest):
    logger.info(f"Получен запрос: {request}")

    try:
        # 1. Пытаемся найти аккаунт (если его нет - получим 404)
        account = find_account_by_phone(request.phone_number)
        return account

    except HTTPException as e:
        if e.status_code != 404:
            raise  # Пробрасываем другие ошибки

        # 2. Если аккаунта нет (404) - создаём новый
        logger.info("Аккаунт не найден, генерируем новый...")
        new_account = generate_random_account()
        if not new_account:
            raise HTTPException(500, "Ошибка генерации счета")

        # 3. Сохраняем в БД
        conn = None
        try:
            conn = connect_to_db()
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO account (phone_number, pam, bank, account)
                    VALUES (%s, %s, %s, %s)
                    RETURNING account
                    """,
                    (request.phone_number, request.pam, "", new_account)
                )
                saved_account = cursor.fetchone()[0]
                conn.commit()

        except Exception as e:
            logger.error(f"Ошибка БД: {e}")
            raise HTTPException(500, "Ошибка при сохранении")
        finally:
            if conn:
                conn.close()

def find_account_by_phone(phone_number: str) -> str:
    """Поиск номера счета по номеру телефона в PostgreSQL"""
    conn = None
    try:
        conn = connect_to_db()
        with conn.cursor() as cursor:
            query = sql.SQL("SELECT account FROM account WHERE phone_number = %s")
            cursor.execute(query, (phone_number,))
            result = cursor.fetchone()
            if not result:
                raise HTTPException(status_code=404, detail="Account not found")
            return result[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query error: {str(e)}")
    finally:
        if conn:
            conn.close()

@app.post("/get_account")
def get_account(request: PhoneRequest):
    """Возвращает реквизиты счета по номеру телефона из PostgreSQL"""
    phone_normalized = request.phone
    if phone_normalized.startswith("+7"):
        phone_normalized = "8" + phone_normalized[2:]
    elif phone_normalized.startswith("7"):
        phone_normalized = "8" + phone_normalized[1:]

    try:
        account = find_account_by_phone(phone_normalized)
        return {"phone": request.phone, "account": account}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/create_link")
def create_payment_link(request: CreateLinkRequest):
    """Создает платежную ссылку и возвращает ее"""
    conn = None
    try:
        conn = connect_to_db()
        with conn.cursor() as cursor:
            query = sql.SQL("""
                INSERT INTO links
                (account_recipient, amount, bank_recipient,
                 pay_message, additionally, disposable, status)
                VALUES (%s, %s, %s, %s, %s, %s, FALSE)
                RETURNING id
            """)
            cursor.execute(query, (
                request.account_recipient,
                request.amount,
                request.bank_recipient,
                request.pay_message,
                request.additionally,
                request.disposable
            ))

            link_id = cursor.fetchone()[0]
            conn.commit()

            return f"http://212.233.98.238:8001/main_sdk.html?id={link_id}"

    except Exception as e:
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        if conn:
            conn.close()

@app.get("/get_link_data/{link_id}", response_model=LinkDataResponse)
def get_link_data(link_id: int):
    """Получает данные платежа по ID ссылки"""
    conn = None
    print(f"🔍 ДЕБАГ: get_link_data для link_id={link_id}")
    try:
        conn = connect_to_db()
        with conn.cursor() as cursor:
            query = sql.SQL("""
                SELECT l.account_recipient, l.amount, l.bank_recipient,
                       l.pay_message, l.additionally, a.pam, a.phone_number,
                       l.status, l.disposable
                FROM links l
                JOIN account a ON l.account_recipient = a.account
                WHERE l.id = %s
            """)
            cursor.execute(query, (link_id,))
            result = cursor.fetchone()

            if not result:
                raise HTTPException(status_code=404, detail="Link not found")

            status = result[7]
            disposable = result[8]
            print(f"🔍 ДЕБАГ: status={status}, disposable={disposable}")

            # 🔴 ИСПРАВЛЕНИЕ: Для открытых сборов НЕ проверяем прогресс при первоначальном запросе
            # Открытые сборы всегда должны начинаться с активной ссылки
            if not status:
                transfer_data = get_transfer_by_link_id_from_link_db(link_id)
                payers_str = transfer_data.get('payers', '') if transfer_data else ''
                is_collective = payers_str and ',' in payers_str
                is_open_collection = payers_str == ''  # Пустой список плательщиков = открытый сбор

                print(f"🔍 ДЕБАГ: is_collective={is_collective}, is_open_collection={is_open_collection}, payers_str='{payers_str}'")

                # 🔴 ИСПРАВЛЕНИЕ: Для открытых сборов НЕ проверяем завершенность при первом запросе
                if is_collective:  # Только для обычных коллективных сборов
                    transfer_id = get_transfer_id_by_link_id(link_id)
                    if transfer_id:
                        progress_info = get_payment_progress(transfer_id)
                        if progress_info and progress_info['is_completed']:
                            print(f"🔍 ДЕБАГ: Коллективный сбор завершен, но статус ссылки FALSE")
                            return LinkDataResponse(
                                account_recipient=result[0],
                                amount=result[1],
                                bank_recipient=result[2],
                                pay_message=result[3],
                                additionally=result[4],
                                pam=result[5],
                                phone_number=result[6],
                                status=True
                            )
                # 🔴 ДОБАВЛЕНО: Для открытых сборов оставляем статус как есть
                elif is_open_collection:
                    print(f"🔍 ДЕБАГ: Открытый сбор - оставляем исходный статус {status}")

            return LinkDataResponse(
                account_recipient=result[0],
                amount=result[1],
                bank_recipient=result[2],
                pay_message=result[3],
                additionally=result[4],
                pam=result[5],
                phone_number=result[6],
                status=status
            )

    except Exception as e:
        print(f"🔍 ДЕБАГ: Ошибка в get_link_data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        if conn:
            conn.close()

@app.post("/update_link_status/{link_id}")
def update_link_status(link_id: int, request_data: dict = None):
    """Обновляет статус ссылки и логирует перевод"""
    conn = None
    try:
        print(f"🔍 ДЕБАГ: Начало update_link_status, link_id={link_id}, request_data={request_data}")

        # Получаем данные из запроса (если есть)
        telegram_tag = None
        bank = None
        if request_data:
            telegram_tag = request_data.get('telegram_tag')
            bank = request_data.get('bank')

        print(f"🔍 ДЕБАГ: telegram_tag={telegram_tag}, bank={bank}")

        conn = connect_to_db()
        with conn.cursor() as cursor:
            # Получаем информацию о ссылке
            cursor.execute("""
                SELECT account_recipient, amount, bank_recipient,
                       pay_message, disposable, status
                FROM links WHERE id = %s FOR UPDATE
            """, (link_id,))
            link_data = cursor.fetchone()

            if not link_data:
                print(f"🔍 ДЕБАГ: Ссылка не найдена")
                raise HTTPException(status_code=404, detail="Ссылка не найдена")

            account, amount, bank_recipient, message, disposable, status = link_data
            print(f"🔍 ДЕБАГ: link_data: account={account}, amount={amount}, status={status}, disposable={disposable}")

            # Получаем информацию о переводе для определения типа
            transfer_data = get_transfer_by_link_id_from_link_db(link_id)
            payers_str = transfer_data.get('payers', '') if transfer_data else ''
            is_collective = payers_str and ',' in payers_str
            is_open_collection = payers_str == ''  # Пустой список плательщиков = открытый сбор

            print(f"🔍 ДЕБАГ: is_collective = {is_collective}, is_open_collection = {is_open_collection}, payers_str = '{payers_str}'")

            # 🔴 РЕАЛЬНАЯ ЛОГИКА ОБРАБОТКИ ССЫЛОК
            if is_collective or is_open_collection:
                # КОЛЛЕКТИВНЫЙ ИЛИ ОТКРЫТЫЙ СБОР - умная логика
                transfer_id = get_transfer_id_by_link_id(link_id)
                print(f"🔍 ДЕБАГ: Коллективный/открытый сбор, transfer_id={transfer_id}")

                if transfer_id:
                    progress_info = get_payment_progress(transfer_id)
                    print(f"🔍 ДЕБАГ: Прогресс сбора: {progress_info}")

                    if progress_info:
                        if is_open_collection:
                            print(f"🔍 ДЕБАГ: Открытый сбор - игнорируем is_completed")
                        elif progress_info['is_completed']:
                            print(f"🔍 ДЕБАГ: Коллективный сбор завершен, ссылка недействительна")
                            raise HTTPException(status_code=400, detail="Сбор уже завершен")
                        else:
                            # Сбор еще не завершен - обновляем прогресс
                            print(f"🔍 ДЕБАГ: Сбор НЕ завершен, обновляем прогресс")
                    else:
                        print(f"🔍 ДЕБАГ: Не удалось получить прогресс, проверяем статус ссылки")
                        if status:
                            raise HTTPException(status_code=400, detail="Ссылка уже использована")
                else:
                    print(f"🔍 ДЕБАГ: Не найден transfer_id, проверяем статус ссылки")
                    if status:
                        raise HTTPException(status_code=400, detail="Ссылка уже использована")
            else:
                # ОДИНОЧНЫЙ ПЕРЕВОД - стандартная логика
                print(f"🔍 ДЕБАГ: Одиночный перевод, проверяем статус")
                if status:
                    print(f"🔍 ДЕБАГ: Ссылка УЖЕ использована")
                    raise HTTPException(status_code=400, detail="Ссылка уже использована")

            # 🔴 РЕАЛЬНОЕ ОБНОВЛЕНИЕ СТАТУСА ССЫЛКИ
            if not (is_collective or is_open_collection):
                # Одиночные переводы - сразу закрываем
                print(f"🔍 ДЕБАГ: Закрываем одиночную ссылку")
                cursor.execute("UPDATE links SET status = TRUE WHERE id = %s", (link_id,))
                conn.commit()
            else:
                # Коллективные/открытые сборы - проверяем, не пора ли закрыть
                transfer_id = get_transfer_id_by_link_id(link_id)
                if transfer_id:
                    progress_info = get_payment_progress(transfer_id)
                    if progress_info and progress_info['is_completed']:
                        print(f"🔍 ДЕБАГ: Все оплатили! Закрываем ссылку")
                        cursor.execute("UPDATE links SET status = TRUE WHERE id = %s", (link_id,))
                        conn.commit()
                    else:
                        print(f"🔍 ДЕБАГ: Еще не все оплатили, оставляем ссылку активной")
                else:
                    print(f"🔍 ДЕБАГ: Не найден transfer_id, оставляем ссылку как есть")

            # Логируем в консоль сервера
            log_data = {
                "link_id": link_id,
                "telegram_tag": telegram_tag,
                "bank": bank,
                "is_collective": is_collective,
                "is_open_collection": is_open_collection,
                "amount": amount
            }
            print(f"💰 ОПЛАТА УСПЕШНА: {log_data}")

            # 🔴 ДОБАВЛЯЕМ ПЛАТЕЛЬЩИКА В СТАТИСТИКУ ДЛЯ ОТКРЫТЫХ СБОРОВ
            if is_open_collection and telegram_tag and transfer_id:
                try:
                    conn_link = connect_to_db_link()
                    with conn_link.cursor() as cursor_link:
                        # Получаем текущих плательщиков
                        cursor_link.execute("SELECT payers FROM transfer WHERE id = %s", (transfer_id,))
                        result = cursor_link.fetchone()
                        current_payers = result[0] if result and result[0] else ""

                        # Добавляем нового плательщика
                        payer_username = telegram_tag.lstrip('@')
                        if current_payers:
                            # Проверяем, не добавлен ли уже этот плательщик
                            existing_payers = [p.strip() for p in current_payers.split(',')]
                            if payer_username not in existing_payers:
                                updated_payers = current_payers + f", {payer_username}"
                            else:
                                updated_payers = current_payers
                        else:
                            updated_payers = payer_username

                        # Обновляем только если изменились плательщики
                        if updated_payers != current_payers:
                            cursor_link.execute(
                                "UPDATE transfer SET payers = %s WHERE id = %s",
                                (updated_payers, transfer_id)
                            )
                            conn_link.commit()
                            print(f"🔍 ДЕБАГ: Добавлен плательщик {payer_username} в открытый сбор {transfer_id}")
                        else:
                            print(f"🔍 ДЕБАГ: Плательщик {payer_username} уже есть в открытом сборе {transfer_id}")

                except Exception as e:
                    print(f"🔍 ДЕБАГ: Ошибка добавления плательщика: {str(e)}")
                finally:
                    if conn_link:
                        conn_link.close()

            # 🔴 ОТПРАВЛЯЕМ УВЕДОМЛЕНИЯ (после обновления статистики)
            if transfer_data and 'recipient' in transfer_data:
                transfer_id = get_transfer_id_by_link_id(link_id)

                if transfer_id:
                    # Обогащаем данные для уведомлений
                    transfer_data['link_id'] = link_id
                    transfer_data['id'] = transfer_id

                    print(f"🔍 ДЕБАГ: Отправляем уведомления с полными данными")
                    send_transfer_notifications(
                        transfer_data=transfer_data,
                        amount=str(amount),
                        message=message,
                        telegram_tag=telegram_tag,
                        bank=bank
                    )
                else:
                    print(f"🔍 ДЕБАГ: Отправляем уведомления без прогресса")
                    send_transfer_notifications(transfer_data, str(amount), message, telegram_tag, bank)
            else:
                print(f"🔍 ДЕБАГ: Нет данных перевода для уведомлений")

            print(f"🔍 ДЕБАГ: Успешное завершение обработки оплаты")
            return {
                "status": "success",
                "message": "Перевод выполнен успешно",
                "link_id": link_id,
                "is_collective": is_collective,
                "is_open_collection": is_open_collection,
                "amount": amount
            }

    except HTTPException:
        raise
    except Exception as e:
        print(f"🔍 ДЕБАГ: ОШИБКА в update_link_status: {str(e)}")
        print(f"🔍 ДЕБАГ: Traceback: {traceback.format_exc()}")
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервера: {str(e)}")
    finally:
        if conn:
            conn.close()



@app.get("/get_transfer_by_link/{id_link}", response_model=TransferResponse)
def get_transfer_by_link(id_link: str):
    """Получает данные перевода по id_link"""
    conn = None
    try:
        conn = connect_to_db_link()
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT recipient, payers, ammount, details
                FROM transfer
                WHERE id_link = %s
            """, (id_link,))
            result = cursor.fetchone()
            print(type(result), result[0])
            if not result:
                raise HTTPException(status_code=404, detail="Transfer not found")

            return TransferResponse(
                recipient=result[0],
                payers=result[1],
                ammount=result[2],
                details=result[3],
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            conn.close()
