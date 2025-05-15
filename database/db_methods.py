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
        default_categories = json.dumps([], ensure_ascii=False)
        await db.execute(
            "INSERT OR IGNORE INTO users (tg_id, tg_username, categories, total_sum) VALUES (?, ?, ?, 0.0)",
            (tg_id, tg_username, default_categories)
        )
        await db.commit()


async def update_user(tg_id: int, **kwargs: Any) -> None:
    """
    обновление информации о пользователе. обновляются только переданные поля.

    аргументы:
        tg_id (int): Telegram ID пользователя.
        **kwargs: Произвольные поля для обновления (name, tg_username, total_sum, categories).
    """
    async with aiosqlite.connect(DB_PATH) as db:
        if not kwargs:
            return

        if "categories" in kwargs and not isinstance(kwargs["categories"], str):
            kwargs["categories"] = json.dumps(kwargs["categories"], ensure_ascii=False)

        fields = ", ".join(f"{key} = ?" for key in kwargs.keys())
        values = list(kwargs.values()) + [tg_id]
        query = f"UPDATE users SET {fields} WHERE tg_id = ?"
        await db.execute(query, values)
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
        cursor = await db.execute(
            "SELECT tg_id, categories, tg_username, name, total_sum FROM users WHERE tg_id = ?",
            (tg_id,)
        )
        row = await cursor.fetchone()
        if row:
            return {
                "tg_id": row[0],
                "categories": json.loads(row[1]),
                "tg_username": row[2],
                "name": row[3],
                "total_sum": row[4]
            }
        return None


async def delete_user(tg_id: int) -> None:
    """
    удаление пользователя и всех связанных данных (транзакции, лимиты) по tg_id.

    аргументы:
        tg_id (int): Telegram ID пользователя.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM users WHERE tg_id = ?", (tg_id,))
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
        date_time = datetime.now().isoformat()
        cursor = await db.execute(
            "INSERT INTO transactions (tg_id, date_time, type, description, category, sum) VALUES (?, ?, ?, ?, ?, ?)",
            (tg_id, date_time, type_, description, category, sum_)
        )
        await db.commit()
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
        cursor = await db.execute(
            "SELECT transaction_id, date_time, type, description, category, sum "
            "FROM transactions WHERE tg_id = ? ORDER BY date_time DESC LIMIT ?",
            (tg_id, limit)
        )
        rows = await cursor.fetchall()
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
        cursor = await db.execute(
            "INSERT INTO limits (tg_id, start_date, end_date, category, limit_sum) VALUES (?, ?, ?, ?, ?)",
            (tg_id, start_date, end_date, category, limit_sum)
        )
        await db.commit()
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
        cursor = await db.execute(
            "SELECT limit_id, start_date, end_date, category, limit_sum "
            "FROM limits WHERE tg_id = ? ORDER BY start_date",
            (tg_id,)
        )
        rows = await cursor.fetchall()
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
        bool: True, если пользователь существует в базе, False в противном случае.
    """
    user = await get_user(tg_id)
    # Логирование для отладки
    print(f"Checking registration for tg_id={tg_id}: user={user}")
    # Проверяем только наличие записи в базе
    return bool(user)


async def add_category(tg_id: int, category: str) -> None:
    """
    Добавление новой категории в список категорий пользователя.

    Аргументы:
        tg_id (int): Telegram ID пользователя.
        category (str): Название новой категории.
    """
    user = await get_user(tg_id)
    if not user:
        raise ValueError("Пользователь не найден")

    categories = user["categories"]
    if category not in categories:
        categories.append(category)
        await update_user(tg_id, categories=categories)
    else:
        raise ValueError("Категория уже существует")


async def get_categories(tg_id: int) -> List[str]:
    """
    Получение списка категорий пользователя.

    Аргументы:
        tg_id (int): Telegram ID пользователя.

    Возвращает:
        List[str]: Список категорий пользователя.
    """
    user = await get_user(tg_id)
    if not user:
        raise ValueError("Пользователь не найден")
    return user["categories"]


async def update_categories(tg_id: int, new_categories: List[str]) -> None:
    """
    Полное замещение списка категорий пользователя новым списком.

    Аргументы:
        tg_id (int): Telegram ID пользователя.
        new_categories (List[str]): Новый список категорий.
    """
    user = await get_user(tg_id)
    if not user:
        raise ValueError("Пользователь не найден")
    categories_json = json.dumps(new_categories, ensure_ascii=False)
    await update_user(tg_id, categories=categories_json)


async def get_transactions_by_period(tg_id: int, start_date: str, end_date: str) -> List[Dict[str, Any]]:
    """
    Получение списка транзакций пользователя за указанный период.

    Аргументы:
        tg_id (int): Telegram ID пользователя.
        start_date (str): Начальная дата периода в формате ISO (например, "2023-10-01").
        end_date (str): Конечная дата периода в формате ISO (например, "2023-10-31").

    Возвращает:
        List[Dict[str, Any]]: Список словарей с данными о транзакциях.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT transaction_id, date_time, type, description, category, sum "
            "FROM transactions WHERE tg_id = ? AND date_time >= ? AND date_time < ? ORDER BY date_time",
            (tg_id, start_date, end_date)
        )
        rows = await cursor.fetchall()
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
