from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, constr
from fastapi.middleware.cors import CORSMiddleware
import psycopg2
from psycopg2 import sql
from typing import Optional
import random
import logging
import requests
import os  # <- ДОБАВЬТЕ ЭТОТ ИМПОРТ
from dotenv import load_dotenv  # <- ДОБАВЬТЕ ЭТОТ ИМПОРТ

load_dotenv()  # <- ДОБАВЬТЕ ЭТУ СТРОКУ

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


# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://host:port", "http://host:port2"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    # expose_headers=["Server"]  # Убираем стандартные заголовки
)


class RegistrationRequest(BaseModel):
    phone_number: str
    pam: str


class PhoneRequest(BaseModel):
    phone: constr(pattern=r"^(\+7|8)\d{10}$")


# Добавим новый класс для запроса на создание ссылки
class CreateLinkRequest(BaseModel):
    account_recipient: constr(pattern=r"^\d{20}$")
    amount: int
    bank_recipient: str
    pay_message: Optional[constr(max_length=140)] = None
    additionally: Optional[str] = None
    disposable: bool


# Добавим модель для ответа с данными ссылки
class LinkDataResponse(BaseModel):
    account_recipient: str
    amount: int
    bank_recipient: str
    pay_message: Optional[str]
    additionally: Optional[str]
    pam: str
    phone_number: str
    status: bool  # Добавляем поле status


class TransferResponse(BaseModel):
    recipient: str
    payers: Optional[str]
    ammount: str
    details: Optional[str]


def connect_to_db():
    try:
        conn = psycopg2.connect(
            dbname="name",
            user="postgres",
            password="password",
            host="host",
            port="dbPort"
        )
        return conn
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database connection error: {str(e)}")


def connect_to_db_link():
    try:
        conn = psycopg2.connect(
            dbname="link2pay",
            user="postgres",
            password="password",
            host="host",
            port="dbPort"
        )
        return conn
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database connection error: {str(e)}")


def generate_random_account() -> str:
    """Генерация валидного 20-значного номера счета"""
    return ''.join(str(random.randint(0, 9)) for _ in range(20))


# Добавляем новый класс для логов
class LogData(BaseModel):
    link_id: int


# Новый эндпоинт для обработки логов от бота
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
            success_msg = f"✅ Перевод {recipient_username} успешен!"
            logger.info(f"Уведомление для {cid_prs}: {success_msg}")

        return {"status": "success"}

    except Exception as e:
        logger.error(f"Ошибка в обработчике логов: {str(e)}")
        return {"status": "error", "message": str(e)}


# Вспомогательная функция для получения chat_id по username
def get_chat_by_username(username: str) -> Optional[int]:
    """Получает chat_id по username из базы данных"""
    conn = None
    try:
        conn = connect_to_db_link()  # Используем то же подключение, что и для transfer
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
        raise  # Пробрасываем HTTPException дальше
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

            return f"http://193.33.153.154:5500/main_sdk.html?id={link_id}"

    except Exception as e:
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        if conn:
            conn.close()


# Обновляем endpoint
@app.get("/get_link_data/{link_id}", response_model=LinkDataResponse)
def get_link_data(link_id: int):
    """Получает данные платежа по ID ссылки"""
    conn = None
    print("dfb")
    try:
        conn = connect_to_db()
        with conn.cursor() as cursor:
            query = sql.SQL("""
                SELECT l.account_recipient, l.amount, l.bank_recipient, 
                       l.pay_message, l.additionally, a.pam, a.phone_number,
                       l.status
                FROM links l
                JOIN account a ON l.account_recipient = a.account
                WHERE l.id = %s
            """)
            cursor.execute(query, (link_id,))
            result = cursor.fetchone()

            if not result:
                raise HTTPException(status_code=404, detail="Link not found")

            return LinkDataResponse(
                account_recipient=result[0],
                amount=result[1],
                bank_recipient=result[2],
                pay_message=result[3],
                additionally=result[4],
                pam=result[5],
                phone_number=result[6],
                status=result[7]
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        if conn:
            conn.close()


@app.post("/update_link_status/{link_id}")
def update_link_status(link_id: int):
    """Обновляет статус ссылки и логирует перевод"""
    conn = None
    try:
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
                raise HTTPException(status_code=404, detail="Ссылка не найдена")

            account, amount, bank, message, disposable, status = link_data

            # Проверяем не использована ли уже ссылка
            if status and disposable:
                raise HTTPException(status_code=400, detail="Ссылка уже использована")

            # Если ссылка одноразовая - обновляем статус
            if disposable:
                cursor.execute("""
                    UPDATE links SET status = TRUE WHERE id = %s
                """, (link_id,))
                conn.commit()

            # Логируем в консоль сервера
            log_data = {
                "link_id": link_id,
            }
            print(f"Отправка лога в бот: {log_data}")

            # Получаем информацию о переводе для уведомлений
            transfer_data = get_transfer_by_link_id_from_link_db(link_id)
            if transfer_data and 'recipient' in transfer_data:
                # Отправляем уведомление получателю
                send_transfer_notifications(transfer_data, amount, message)
            return {"success": True}

    except Exception as e:
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            conn.close()


def get_transfer_by_link_id_from_link_db(link_id: int):
    """Получает данные перевода из базы link2pay"""
    conn = None
    try:
        conn = connect_to_db_link()
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT recipient, payers, ammount, details
                FROM transfer
                WHERE id_link = %s
            """, (str(link_id),))
            result = cursor.fetchone()

            if result:
                return {
                    'recipient': result[0],
                    'payers': result[1],
                    'amount': result[2],
                    'details': result[3]
                }
            return None
    except Exception as e:
        logger.error(f"Ошибка получения данных перевода: {str(e)}")
        return None
    finally:
        if conn:
            conn.close()


def send_transfer_notifications(transfer_data: dict, amount: str, message: str):
    """Отправляет уведомления о переводе"""
    try:
        # Получаем chat_id получателя
        recipient_username = transfer_data.get('recipient')
        recipient_chat_id = get_chat_by_username(recipient_username)

        # Отправляем уведомление получателю
        if recipient_chat_id:
            notification_text = f"💸 Вам перевод {amount} ₽\n"

            payers = transfer_data.get('payers', '')
            if payers:
                notification_text += f"От: @{payers}\n"

            details = transfer_data.get('details')
            if details:
                notification_text += f"Сообщение: {details}"

            send_telegram_notification(recipient_chat_id, notification_text)
            logger.info(f"Уведомление отправлено получателю {recipient_username}")

        # Отправляем уведомления отправителям (для запросов)
        payers_str = transfer_data.get('payers', '')
        if payers_str and ',' in payers_str:
            # Это запрос с несколькими плательщиками
            payer_usernames = [p.strip() for p in payers_str.split(',')]
            for payer_username in payer_usernames:
                payer_chat_id = get_chat_by_username(payer_username)
                if payer_chat_id:
                    success_text = f"✅ Перевод {recipient_username} успешен!"
                    send_telegram_notification(payer_chat_id, success_text)

    except Exception as e:
        logger.error(f"Ошибка отправки уведомлений: {str(e)}")


# APINIKITKA.py

# Добавляем новый класс для ответа


# Новый эндпоинт
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
