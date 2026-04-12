import os
import psycopg2
from psycopg2 import extras
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

@dataclass
class User:
    chat_id: int
    username: str
    name: str
    phone: str
    messenger_type: str = 'telegram'
    id_user: Optional[int] = None


class Database:
    def __init__(self):
        pass

    def _create_connection(self):
        """Создает новое подключение к PostgreSQL (link2pay)"""
        return psycopg2.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=os.getenv('DB_PORT', '5432'),
            dbname=os.getenv('DB_NAME', 'link2pay'),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASS', 'password'),
            connect_timeout=5
        )

    def _execute(self, query, params=None):
        """Универсальный метод выполнения запросов"""
        try:
            with self._create_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, params or ())
                    conn.commit()
                    if cur.description:
                        return cur.fetchall()
                    return None
        except psycopg2.OperationalError as e:
            raise Exception(f"Ошибка подключения: {str(e)}")

    def save_user(self, user: User):
        """Сохраняет пользователя в базу данных"""
        query = """
            INSERT INTO users(chat_id, username, name, phone, messenger_type)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (chat_id) DO UPDATE SET
                username = EXCLUDED.username,
                name = EXCLUDED.name,
                phone = EXCLUDED.phone,
                messenger_type = EXCLUDED.messenger_type
            RETURNING id_user
        """
        result = self._execute(query, (user.chat_id, user.username, user.name, user.phone, user.messenger_type))
        if result:
            user.id_user = result[0][0]

    def delete_user(self, chat_id: int):
        """Удаляет пользователя по chat_id"""
        query = "DELETE FROM users WHERE chat_id = %s"
        try:
            self._execute(query, (chat_id,))
            return True
        except Exception as e:
            print(f"Ошибка при удалении пользователя: {str(e)}")
            return False

    def get_user_by_chat(self, chat_id: int) -> Optional[User]:
        """Получает пользователя по chat_id"""
        query = """
            SELECT chat_id, username, name, phone, id_user, messenger_type
            FROM users WHERE chat_id = %s
        """
        result = self._execute(query, (chat_id,))
        if result:
            row = result[0]
            return User(
                chat_id=row[0],
                username=row[1],
                name=row[2],
                phone=row[3],
                id_user=row[4],
                messenger_type=row[5] if len(row) > 5 else 'telegram'
            )
        return None

    def get_user_by_username(self, username: str) -> Optional[User]:
        """Получает пользователя по username (регистронезависимо)"""
        query = """
            SELECT chat_id, username, name, phone, id_user, messenger_type
            FROM users WHERE LOWER(username) = LOWER(%s)
        """
        result = self._execute(query, (username,))
        if result:
            row = result[0]
            return User(
                chat_id=row[0],
                username=row[1],
                name=row[2],
                phone=row[3],
                id_user=row[4],
                messenger_type=row[5] if len(row) > 5 else 'telegram'
            )
        return None

    def get_chat_by_username(self, username: str) -> Optional[int]:
        """Получает chat_id по username"""
        query = "SELECT chat_id FROM users WHERE LOWER(username) = LOWER(%s)"
        result = self._execute(query, (username,))
        return result[0][0] if result else None

    def is_phone_taken_by_other(self, phone: str, chat_id: int) -> bool:
        """Проверяет, используется ли телефон другим пользователем"""
        query = "SELECT chat_id FROM users WHERE phone = %s"
        result = self._execute(query, (phone,))
        return result and result[0][0] != chat_id

    def addTransfer(self, recipient: str, payers: list, amount: str, details: str, link_id: int):
        """Сохраняет данные перевода в базу данных"""
        try:
            payers_str = ', '.join(payers)

            query = """
                INSERT INTO transfer
                (recipient, payers, ammount, details, id_link)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
            """
            result = self._execute(query, (
                recipient,
                payers_str,
                amount,
                details,
                str(link_id)
            ))

            if result:
                return result[0][0]
            return None

        except Exception as e:
            print(f"Ошибка при сохранении перевода: {str(e)}")
            return None

    def has_previous_transfers(self, sender_username: str, recipient_username: str) -> bool:
        """Проверяет, были ли ранее переводы между пользователями"""
        try:
            query = """
                SELECT COUNT(*) FROM transfer
                WHERE (LOWER(recipient) = LOWER(%s) AND LOWER(payers) LIKE LOWER(%s))
                   OR (LOWER(recipient) = LOWER(%s) AND LOWER(payers) LIKE LOWER(%s))
            """
            sender_pattern = f'%{sender_username}%'
            recipient_pattern = f'%{recipient_username}%'

            result = self._execute(query, (
                recipient_username, sender_pattern,
                sender_username, recipient_pattern
            ))

            if result and result[0][0] > 0:
                return True
            return False

        except Exception as e:
            print(f"Ошибка при проверке истории переводов: {str(e)}")
            return False


# Глобальный экземпляр базы данных
db = Database()
