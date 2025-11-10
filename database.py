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
    id_user: Optional[int] = None
    id_user: Optional[int] = None

class Database:
    def __init__(self):
       pass

    def _create_connection(self):
        """Создает новое подключение к PostgreSQL"""
        return psycopg2.connect(
            host=os.getenv('DB_HOST', 'host'),
            port=os.getenv('DB_PORT', 'port'),
            dbname=os.getenv('DB_NAME', 'opkc'),
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
                    if cur.description:  # Для SELECT и аналогичных запросов
                        return cur.fetchall()
                    return None
        except psycopg2.OperationalError as e:
            raise Exception(f"Ошибка подключения: {str(e)}")
    def save_user(self, user: User):
        """Сохраняет пользователя в базу данных"""
        query = """
            INSERT INTO users(chat_id, username, name, phone)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (chat_id) DO UPDATE SET
                username = EXCLUDED.username,
                name = EXCLUDED.name,
                phone = EXCLUDED.phone
            RETURNING id_user
        """
        result = self._execute(query, (user.chat_id, user.username, user.name, user.phone))
        if result:  # Пример результата: [(123,)]
            user.id_user = result[0][0]  # Достаем id_user из первого элемента
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
            SELECT chat_id, username, name, phone, id_user
            FROM users WHERE chat_id = %s
        """
        result = self._execute(query, (chat_id,))
        if result:
            row = result[0]  # Первая запись из результата
            return User(
                chat_id=row[0],
                username=row[1],
                name=row[2],
                phone=row[3],
                id_user=row[4]
            )
        return None

    def get_user_by_username(self, username: str) -> Optional[User]:
        """Получает пользователя по username"""
        query = """
            SELECT chat_id, username, name, phone, id_user
            FROM users WHERE username = %s
        """
        result = self._execute(query, (username,))
        if result:
            row = result[0]  # Первая строка результата
            return User(
                chat_id=row[0],
                username=row[1],
                name=row[2],
                phone=row[3],
                id_user=row[4]
            )
        return None

    def get_chat_by_username(self, username: str) -> Optional[int]:
        """Получает chat_id по username"""
        query = "SELECT chat_id FROM users WHERE username = %s"
        result = self._execute(query, (username,))
        return result[0][0] if result else None  # Первая строка, первый столбец
    def is_phone_taken_by_other(self, phone: str, chat_id: int) -> bool:
        """Проверяет, используется ли телефон другим пользователем"""
        query = "SELECT chat_id FROM users WHERE phone = %s"
        result = self._execute(query, (phone,))
        return result and result[0][0] != chat_id  # result[0][0] — chat_id из БД

    def addTransfer(self, recipient: str, payers: list, amount: str, details: str, link_id: int):
        """Сохраняет данные перевода в базу данных"""
        try:
            #Преобразуем список плательщиков в строку

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
                return result[0][0]  # Возвращаем ID созданной записи
            return None

        except Exception as e:
            print(f"Ошибка при сохранении перевода: {str(e)}")
            return None
    def has_previous_transfers(self, sender_username: str, recipient_username: str) -> bool:
        """Проверяет, были ли ранее переводы между пользователями (точная проверка)"""
        try:
            query = """
                SELECT COUNT(*) FROM transfer
                WHERE (recipient = %s AND (payers = %s OR payers LIKE %s OR payers LIKE %s OR payers LIKE %s))
                   OR (recipient = %s AND (payers = %s OR payers LIKE %s OR payers LIKE %s OR payers LIKE %s))
            """
            # Варианты расположения username в поле payers:
            # - Только этот пользователь: "username"
            # - Первый в списке: "username, ..."
            # - В середине списка: "..., username, ..."
            # - Последний в списке: "..., username"
            
            sender_pattern_start = f'{sender_username}, %'
            sender_pattern_middle = f'%, {sender_username}, %'
            sender_pattern_end = f'%, {sender_username}'
            
            recipient_pattern_start = f'{recipient_username}, %'
            recipient_pattern_middle = f'%, {recipient_username}, %'
            recipient_pattern_end = f'%, {recipient_username}'
            
            result = self._execute(query, (
                # sender → recipient
                recipient_username, sender_username, sender_pattern_start, sender_pattern_middle, sender_pattern_end,
                # recipient → sender  
                sender_username, recipient_username, recipient_pattern_start, recipient_pattern_middle, recipient_pattern_end
            ))
            
            if result and result[0][0] > 0:
                return True  # Переводы были
            return False  # Переводов не было
            
        except Exception as e:
            print(f"Ошибка при проверке истории переводов: {str(e)}")
            return False

# Глобальный экземпляр базы данных
db = Database()
