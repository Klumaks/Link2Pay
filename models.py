import requests
from dataclasses import dataclass, field
from typing import List
from database import db
import json
from urllib.parse import quote_plus

APINIKITKA_BASE_URL = 'http://193.33.153.154:8000'  # Замените на ваш URL API

def clean_message_for_api(message: str) -> str:
    """Очищает сообщение от эмодзи для API"""
    if not message:
        return None
    
    # Убираем эмодзи из предустановленных целей
    emoji_cleanup = {
        "🍽️ За ресторан": "За ресторан",
        "🚕 За такси": "За такси", 
        "🎁 На подарок": "На подарок",
        "💰 Возврат долга": "Возврат долга",
        "💸 На карманные расходы": "На карманные расходы"
    }
    
    return emoji_cleanup.get(message, message)

def get_transfer_info(link_id: str) -> dict:
    """Запрашивает данные перевода по API"""
    try:
        response = requests.get(
            f"http://193.33.153.154:8000/get_transfer_by_link/{link_id}",
            timeout=5
        )
        response.raise_for_status()
        return response.json()

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return {"error": "Перевод не найден"}
        return {"error": f"Ошибка сервера: {e.response.status_code}"}

    except Exception as e:
        return {"error": f"Ошибка соединения: {str(e)}"}

def checkDisposable(payers:str):
    if len(payers) ==1:
        return True
    else:
        return False

def registr_account_by_phone(phone_number: str, pam: str):
    try:
        payload = {
            "phone_number": phone_number,
            "pam": pam
        }
        headers = {"Content-Type": "application/json"}
        response = requests.post(
            "http://193.33.153.154:8000/regist_account",
            data=json.dumps(payload),
            headers=headers
        )
        response.raise_for_status()

        return response.json()

    except requests.exceptions.HTTPError as http_err:
        error_msg = f"HTTP ошибка: {http_err}"
        if response.status_code == 400:
            error_msg = "Неверные параметры запроса"
        return {"error": error_msg}
    except Exception as err:
        return {"error": f"Произошла ошибка: {err}"}

@dataclass
class SendFlow:
    chat_id: int
    recipient: str = ''
    amount: str = ''
    details: str = ''
    step: str = 'recipient'

    def generate_link(self) -> str:
        """Генерирует платежную ссылку через API"""
        try:
            # Получаем данные получателя
            recipient_user = db.get_user_by_username(self.recipient)
            if not recipient_user:
                raise ValueError("Получатель не найден")

            # Нормализация номера телефона
            phone = recipient_user.phone
            if phone.startswith("+7"):
                phone = "8" + phone[2:]
            elif phone.startswith("7"):
                phone = "8" + phone[1:]

            # Получаем реквизиты счета
            account_response = requests.post(
                f"http://193.33.153.154:8000/get_account",
                json={"phone": phone},
                timeout=10
            )
            account_response.raise_for_status()
            account = account_response.json().get("account")

            if not account:
                raise ValueError("Не удалось получить реквизиты счета")

            # ОЧИЩАЕМ СООБЩЕНИЕ ОТ ЭМОДЗИ ПЕРЕД ОТПРАВКОЙ В API
            clean_details = clean_message_for_api(self.details)

            payload = {
                "account_recipient": account,
                "amount": self.amount,
                "bank_recipient": "bank1",
                "pay_message": clean_details[:140] if clean_details else None,
                "additionally": "HF39AG4T",
                "disposable": True  # Одиночные переводы всегда одноразовые
            }
            headers = {"Content-Type": "application/json"}

            response = requests.post(
                "http://193.33.153.154:8000/create_link",
                data=json.dumps(payload),
                headers=headers
            )
            response.raise_for_status()

            return response.json()

        except requests.exceptions.RequestException as e:
            raise Exception(f"Ошибка соединения с API: {str(e)}")
        except Exception as e:
            raise Exception(f"Ошибка при генерации ссылки: {str(e)}")

@dataclass
class RequestFlow:
    chat_id: int
    payers: List[str] = field(default_factory=list)
    amount: str = ''
    details: str = ''
    step: str = 'payers'
    is_open_collection: bool = False  # Флаг открытого сбора

    def generate_link(self, payer: str, disposable: bool) -> str:
        """Генерирует ссылку для запроса платежа"""
        try:
            # 🔴 РАЗДЕЛЕНИЕ ЛОГИКИ ПО ТИПУ СБОРА
            if not self.is_open_collection:
                # Обычный сбор - проверяем плательщика
                payer_user = db.get_user_by_username(payer)
                if not payer_user:
                    raise ValueError("Получатель не найден")

                phone = payer_user.phone
                if phone.startswith("+7"):
                    phone = "8" + phone[2:]
                elif phone.startswith("7"):
                    phone = "8" + phone[1:]
            else:
                # Открытый сбор - используем телефон создателя
                requester = db.get_user_by_chat(self.chat_id)
                if not requester:
                    raise ValueError("Создатель сбора не найден")

                phone = requester.phone
                if phone.startswith("+7"):
                    phone = "8" + phone[2:]
                elif phone.startswith("7"):
                    phone = "8" + phone[1:]

            # Общая логика получения счета
            account_response = requests.post(
                f"http://193.33.153.154:8000/get_account",
                json={"phone": phone},
                timeout=10
            )
            account_response.raise_for_status()
            account = account_response.json().get("account")

            if not account:
                raise ValueError("Не удалось получить реквизиты счета")

            # 🔴 НАСТРОЙКА ТИПА ССЫЛКИ
            # Для открытых сборов - многоразовая ссылка (disposable=False)
            # Для обычных сборов - зависит от количества плательщиков
            # 🔴 ИСПРАВЛЕНИЕ: Для открытых сборов ВСЕГДА disposable=False
            if self.is_open_collection:
                final_disposable = False  # Открытые сборы всегда многоразовые
            else:
                final_disposable = disposable  # Обычные сборы по логике checkDisposable

            # ОЧИЩАЕМ СООБЩЕНИЕ ОТ ЭМОДЗИ ПЕРЕД ОТПРАВКОЙ В API
            clean_details = clean_message_for_api(self.details)

            payload = {
                "account_recipient": account,
                "amount": self.amount,
                "bank_recipient": "bank1",
                "pay_message": clean_details[:140] if clean_details else None,
                "additionally": "HF39AG4T",
                "disposable": final_disposable
            }
            headers = {"Content-Type": "application/json"}

            response = requests.post(
                "http://193.33.153.154:8000/create_link",
                data=json.dumps(payload),
                headers=headers
            )
            response.raise_for_status()

            return response.json()

        except requests.exceptions.RequestException as e:
            raise Exception(f"Ошибка соединения с API: {str(e)}")
        except Exception as e:
            raise Exception(f"Ошибка при генерации ссылки: {str(e)}")

def get_confirm(link_id, cid, dest):
    requests.post(
        "http://193.33.153.154:5001/log",
        json={
            "link_id": link_id,
            "cid": cid,
            "dest": dest
        },
        timeout=3
    )

def update_payment_progress(transfer_id: int, link_id: int, payer_username: str, amount: float):
    """Обновляет прогресс платежа для коллективных сборов"""
    conn = None
    try:
        # Используем существующее подключение из database.py
        from database import db
        result = db._execute("""
            INSERT INTO payment_progress (transfer_id, link_id, payer_username, paid_amount)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (transfer_id, payer_username)
            DO UPDATE SET
                paid_amount = EXCLUDED.paid_amount,
                paid_at = CURRENT_TIMESTAMP,
                status = TRUE
            RETURNING id
        """, (transfer_id, link_id, payer_username, amount))

        return bool(result)

    except Exception as e:
        print(f"Ошибка обновления прогресса платежа: {str(e)}")
        return False

def get_payment_progress(transfer_id: int):
    """Получает статистику прогресса платежа"""
    try:
        from database import db

        # Получаем информацию о переводе
        transfer_result = db._execute("""
            SELECT ammount, payers, recipient, details
            FROM transfer
            WHERE id = %s
        """, (transfer_id,))

        if not transfer_result:
            return None

        amount_per_payer = float(transfer_result[0][0])  # Сумма с каждого
        payers_str = transfer_result[0][1]
        recipient = transfer_result[0][2]
        details = transfer_result[0][3]

        # 🔴 ИСПРАВЛЕНИЕ: Корректно определяем тип сбора
        is_open_collection = (payers_str is None or payers_str.strip() == '')
        
        if is_open_collection:
            # 🔴 ОТКРЫТЫЙ СБОР: всегда активен, пока не закрыт вручную
            # Получаем информацию об оплативших
            progress_result = db._execute("""
                SELECT payer_username, paid_amount, paid_at
                FROM payment_progress
                WHERE transfer_id = %s AND status = TRUE
                ORDER BY paid_at
            """, (transfer_id,))

            # Считаем статистику для открытого сбора
            paid_users = []
            actual_payers = len(progress_result) if progress_result else 0
            actual_amount = 0.0

            if progress_result:
                for row in progress_result:
                    paid_users.append({
                        'username': row[0],
                        'amount': float(row[1]),
                        'paid_at': row[2].strftime('%d.%m.%Y %H:%M') if row[2] else None
                    })
                    actual_amount += float(row[1])

            # 🔴 ВАЖНО: Открытые сборы НИКОГДА не завершаются автоматически
            return {
                'target_amount': 0.0,  # Нет целевой суммы
                'actual_amount': actual_amount,
                'amount_per_payer': amount_per_payer,  # Сумма с каждого участника
                'total_payers': 0,  # Нет ограничения по количеству
                'actual_payers': actual_payers,
                'progress_percent': 0,  # Нет процента завершения
                'paid_users': paid_users,
                'unpaid_payers': [],  # Нет списка ожидаемых плательщиков
                'recipient': recipient,
                'details': details,
                'is_completed': False  # 🔴 ВСЕГДА False для открытых сборов
            }
        else:
            # ОБЫЧНЫЙ КОЛЛЕКТИВНЫЙ СБОР - существующая логика
            all_payers = [p.strip() for p in payers_str.split(',')] if payers_str and ',' in payers_str else [payers_str] if payers_str else []
            total_payers = len(all_payers)

            # Получаем информацию об оплативших
            progress_result = db._execute("""
                SELECT payer_username, paid_amount, paid_at
                FROM payment_progress
                WHERE transfer_id = %s AND status = TRUE
                ORDER BY paid_at
            """, (transfer_id,))

            # Считаем статистику
            paid_users = []
            actual_payers = len(progress_result) if progress_result else 0
            actual_amount = 0.0

            if progress_result:
                for row in progress_result:
                    paid_users.append({
                        'username': row[0],
                        'amount': float(row[1]),
                        'paid_at': row[2].strftime('%d.%m.%Y %H:%M') if row[2] else None
                    })
                    actual_amount += float(row[1])

            # Определяем неплательщиков
            paid_usernames = [user['username'] for user in paid_users]
            unpaid_payers = [payer for payer in all_payers if payer not in paid_usernames]

            # Целевая сумма = сумма с каждого × количество плательщиков
            target_amount = amount_per_payer * total_payers

            progress_percent = (actual_amount / target_amount * 100) if target_amount > 0 else 0

            return {
                'target_amount': target_amount,
                'actual_amount': actual_amount,
                'amount_per_payer': amount_per_payer,
                'total_payers': total_payers,
                'actual_payers': actual_payers,
                'progress_percent': round(progress_percent, 1),
                'paid_users': paid_users,
                'unpaid_payers': unpaid_payers,
                'recipient': recipient,
                'details': details,
                'is_completed': actual_payers >= total_payers  # Только для обычных сборов
            }

    except Exception as e:
        print(f"Ошибка получения прогресса платежа: {str(e)}")
        return None

def get_transfer_id_by_link_id(link_id: int):
    """Получает ID перевода по link_id"""
    try:
        from database import db
        result = db._execute("""
            SELECT id FROM transfer WHERE id_link = %s
        """, (str(link_id),))
        return result[0][0] if result else None
    except Exception as e:
        print(f"Ошибка получения transfer_id: {str(e)}")
        return None

def get_transfer_by_link_id_from_link_db(link_id: int):
    """Получает данные перевода из базы link2pay"""
    try:
        from database import db
        result = db._execute("""
            SELECT recipient, payers, ammount, details
            FROM transfer
            WHERE id_link = %s
        """, (str(link_id),))

        if result:
            return {
                'recipient': result[0][0],
                'payers': result[0][1],
                'amount': result[0][2],
                'details': result[0][3]
            }
        return None
    except Exception as e:
        print(f"Ошибка получения данных перевода: {str(e)}")
        return None
