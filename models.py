import requests
from dataclasses import dataclass, field
from typing import List
from database import db
import json
from urllib.parse import quote_plus

APINIKITKA_BASE_URL = 'http://host:port3'  # Замените на ваш URL API






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
            "http://host:port3/regist_account",
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
                f"{APINIKITKA_BASE_URL}/get_account",
                json={"phone": phone},
                timeout=10
            )
            account_response.raise_for_status()
            account = account_response.json().get("account")

            if not account:
                raise ValueError("Не удалось получить реквизиты счета")


            payload = {
                "account_recipient": account,
                "amount": self.amount,
                "bank_recipient": "bank1",
                "pay_message": self.details[:140] if self.details else None,
                "additionally": "HF39AG4T",
                "disposable": True##################################################always true
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
            raise Exception(f"Ошибка при генерации ссылки: {str(e)}")


    # except requests.exceptions.HTTPError as http_err:
    #     error_msg = f"HTTP ошибка: {http_err}"
    #     if response.status_code == 400:
    #         error_msg = "Неверные параметры запроса"
    #     return {"error": error_msg}
    # except Exception as err:
    #     return {"error": f"Произошла ошибка: {err}"}

@dataclass
class RequestFlow:
    chat_id: int
    payers: List[str] = field(default_factory=list)
    amount: str = '666'
    details: str = ''
    step: str = 'payers'


    def generate_link(self, payer: str, disposable:bool) -> str:
        """Генерирует ссылку для запроса платежа"""
        try:
            payer_user = db.get_user_by_username(payer)
            if not payer_user:
                raise ValueError("получатель не найден")

            phone = payer_user.phone
            if phone.startswith("+7"):
                phone = "8" + phone[2:]
            elif phone.startswith("7"):
                phone = "8" + phone[1:]

            account_response = requests.post(
                f"{APINIKITKA_BASE_URL}/get_account",
                json={"phone": phone},
                timeout=10
            )
            account_response.raise_for_status()
            account = account_response.json().get("account")

            if not account:
                raise ValueError("Не удалось получить реквизиты счета")

            payload={
                "account_recipient": account,
                "amount": self.amount,
                "bank_recipient": "bank1",
                "pay_message": self.details[:140] if self.details else None,
                "additionally": "HF39AG4T",
                "disposable": disposable
            }
            headers = {"Content-Type": "application/json"}

            response = requests.post(
                "http://host:port3/create_link",
                data=json.dumps(payload),
                headers=headers
            )
            response.raise_for_status()

            return response.json()

        except requests.exceptions.RequestException as e:
            raise Exception(f"Ошибка соединения с API: {str(e)}")
            raise Exception(f"Ошибка при генерации ссылки: {str(e)}")


def get_confirm(link_id, cid, dest):
    requests.post(
        "http://host:port2/log",
        json={
            "link_id": link_id,
            "cid": cid,
            "dest": dest
        },
        timeout=3
    )
