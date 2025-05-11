import aiosqlite
import json
from typing import Optional, Dict, Any, List
from datetime import datetime

# Путь к базе данных
DB_PATH = "database/data.db"


async def add_user(tg_id: int, tg_username: Optional[str] = None) -> None:
    """
    добавление нового пользователя в базу данных.

    аргументы:
        tg_id (int): Уникальный Telegram ID пользователя.
        tg_username (Optional[str]): Имя пользователя в Telegram (без @), может быть None.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        # инициализация пустого списка категорий по умолчанию
        default_categories = json.dumps([])
        # выполнение запроса на добавление пользователя
        await db.execute(
            "INSERT OR IGNORE INTO users (tg_id, tg_username, categories, total_sum) VALUES (?, ?, ?, 0.0)",
            (tg_id, tg_username, default_categories)
        )
        # сохранение изменений в базе
        await db.commit()


async def update_user(tg_id: int, **kwargs: Any) -> None:
    """
    обновление информации о пользователе. обновляются только переданные поля.

    аргументы:
        tg_id (int): Telegram ID пользователя.
        **kwargs: Произвольные поля для обновления (name, tg_username, total_sum, categories).
    """
    async with aiosqlite.connect(DB_PATH) as db:
        # проверка наличия переданных данных
        if not kwargs:
            # завершение функции, если данных нет
            return

        # преобразование categories в json, если передан список
        if "categories" in kwargs and not isinstance(kwargs["categories"], str):
            kwargs["categories"] = json.dumps(kwargs["categories"])

        # формирование строки с полями для обновления
        fields = ", ".join(f"{key} = ?" for key in kwargs.keys())
        # создание списка значений для запроса
        values = list(kwargs.values()) + [tg_id]

        # формирование sql-запроса
        query = f"UPDATE users SET {fields} WHERE tg_id = ?"
        # выполнение запроса на обновление
        await db.execute(query, values)
        # сохранение изменений в базе
        await db.commit()


async def get_user(tg_id: int) -> Optional[Dict[str, Any]]:
    """
    получение информации о пользователе по tg_id.

    аргументы:
        tg_id (int): Telegram ID пользователя.

    возвращает:
        Dict[str, Any]: Словарь с данными пользователя или None, если пользователь не найден.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        # выполнение запроса на получение данных пользователя
        cursor = await db.execute(
            "SELECT tg_id, categories, tg_username, name, total_sum FROM users WHERE tg_id = ?",
            (tg_id,)
        )
        # получение первой строки результата
        row = await cursor.fetchone()
        # проверка наличия данных
        if row:
            # формирование словаря с данными пользователя
            return {
                "tg_id": row[0],
                "categories": json.loads(row[1]),  # преобразование json обратно в список
                "tg_username": row[2],
                "name": row[3],
                "total_sum": row[4]
            }
        # возврат None, если пользователь не найден
        return None


async def delete_user(tg_id: int) -> None:
    """
    удаление пользователя и всех связанных данных (транзакции, лимиты) по tg_id.

    аргументы:
        tg_id (int): Telegram ID пользователя.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        # выполнение запроса на удаление пользователя
        await db.execute("DELETE FROM users WHERE tg_id = ?", (tg_id,))
        # сохранение изменений в базе (удаление транзакций и лимитов через cascade)
        await db.commit()


async def add_transaction(tg_id: int, type_: int, sum_: float, category: Optional[str] = None,
                          description: Optional[str] = None) -> int:
    """
    добавление новой транзакции в базу данных.

    аргументы:
        tg_id (int): Telegram ID пользователя.
        type_ (int): Тип транзакции (0 = доход, 1 = расход).
        sum_ (float): Сумма транзакции (положительное число).
        category (Optional[str]): Категория транзакции, должна быть в users.categories или None.
        description (Optional[str]): Описание транзакции, может быть None.

    возвращает:
        int: ID добавленной транзакции.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        # получение текущего времени в iso-формате
        date_time = datetime.now().isoformat()
        # выполнение запроса на добавление транзакции
        cursor = await db.execute(
            "INSERT INTO transactions (tg_id, date_time, type, description, category, sum) VALUES (?, ?, ?, ?, ?, ?)",
            (tg_id, date_time, type_, description, category, sum_)
        )
        # сохранение изменений в базе
        await db.commit()
        # возврат id последней добавленной записи
        return cursor.lastrowid


async def get_transactions(tg_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    """
    получение списка последних транзакций пользователя.

    аргументы:
        tg_id (int): Telegram ID пользователя.
        limit (int): Максимальное количество возвращаемых транзакций (по умолчанию 10).

    возвращает:
        List[Dict[str, Any]]: Список словарей с данными о транзакциях.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        # выполнение запроса на получение транзакций
        cursor = await db.execute(
            "SELECT transaction_id, date_time, type, description, category, sum "
            "FROM transactions WHERE tg_id = ? ORDER BY date_time DESC LIMIT ?",
            (tg_id, limit)
        )
        # получение всех строк результата
        rows = await cursor.fetchall()
        # формирование списка словарей с данными транзакций
        return [
            {
                "transaction_id": row[0],
                "date_time": row[1],
                "type": row[2],
                "description": row[3],
                "category": row[4],
                "sum": row[5]
            }
            for row in rows
        ]


async def add_limit(tg_id: int, start_date: str, end_date: str, limit_sum: float,
                    category: Optional[str] = None) -> int:
    """
    добавление нового лимита в базу данных.

    аргументы:
        tg_id (int): Telegram ID пользователя.
        start_date (str): Дата начала лимита в ISO-формате (например, "2025-02-01").
        end_date (str): Дата окончания лимита в ISO-формате (например, "2025-02-28").
        limit_sum (float): Сумма лимита (положительное число).
        category (Optional[str]): Категория лимита, должна быть в users.categories или None.

    возвращает:
        int: ID добавленного лимита.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        # выполнение запроса на добавление лимита
        cursor = await db.execute(
            "INSERT INTO limits (tg_id, start_date, end_date, category, limit_sum) VALUES (?, ?, ?, ?, ?)",
            (tg_id, start_date, end_date, category, limit_sum)
        )
        # сохранение изменений в базе
        await db.commit()
        # возврат id последней добавленной записи
        return cursor.lastrowid


async def get_limits(tg_id: int) -> List[Dict[str, Any]]:
    """
    получение списка всех лимитов пользователя.

    аргументы:
        tg_id (int): Telegram ID пользователя.

    возвращает:
        List[Dict[str, Any]]: Список словарей с данными о лимитах.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        # выполнение запроса на получение лимитов
        cursor = await db.execute(
            "SELECT limit_id, start_date, end_date, category, limit_sum "
            "FROM limits WHERE tg_id = ? ORDER BY start_date",
            (tg_id,)
        )
        # получение всех строк результата
        rows = await cursor.fetchall()
        # формирование списка словарей с данными лимитов
        return [
            {
                "limit_id": row[0],
                "start_date": row[1],
                "end_date": row[2],
                "category": row[3],
                "limit_sum": row[4]
            }
            for row in rows
        ]


async def is_registered(tg_id: int) -> bool:
    """
    проверка, зарегистрирован ли пользователь.

    аргументы:
        tg_id (int): Telegram ID пользователя.

    возвращает:
        bool: True, если пользователь зарегистрирован (есть имя и начальная сумма), False в противном случае.
    """
    user = await get_user(tg_id)
    return bool(user and user["name"] and user["total_sum"] is not None)
