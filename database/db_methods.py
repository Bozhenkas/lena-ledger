"""методы для работы с базой данных sqlite, включая операции с пользователями, транзакциями, категориями и лимитами"""

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


async def delete_user(tg_id: int) -> bool:
    """
    Удаление пользователя и всех связанных с ним данных.

    Аргументы:
        tg_id (int): Telegram ID пользователя.

    Возвращает:
        bool: True, если удаление прошло успешно, False в противном случае.
    """
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # Удаляем транзакции пользователя
            await db.execute('DELETE FROM transactions WHERE tg_id = ?', (tg_id,))
            
            # Удаляем лимиты пользователя
            await db.execute('DELETE FROM limits WHERE tg_id = ?', (tg_id,))
            
            # Очищаем данные пользователя (оставляем запись, но сбрасываем поля)
            await db.execute('''
                UPDATE users 
                SET name = NULL, 
                    total_sum = NULL, 
                    categories = '[]' 
                WHERE tg_id = ?
            ''', (tg_id,))
            
            await db.commit()
            return True
    except Exception as e:
        print(f"Error in delete_user: {e}")
        return False


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


async def add_limit(tg_id: int, start_date: str, end_date: str, category: str, limit_sum: float) -> bool:
    """Добавление нового лимита для пользователя"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO limits (tg_id, start_date, end_date, category, limit_sum) VALUES (?, ?, ?, ?, ?)",
                (tg_id, start_date, end_date, category, limit_sum)
            )
            await db.commit()
            return True
    except Exception as e:
        print(f"Error adding limit: {e}")
        return False


async def get_user_limits(tg_id: int) -> list:
    """Получение всех активных лимитов пользователя"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM limits WHERE tg_id = ? AND end_date >= date('now')",
            (tg_id,)
        )
        return [dict(row) for row in await cursor.fetchall()]


async def delete_limit(limit_id: int, tg_id: int) -> bool:
    """Удаление лимита по его ID"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "DELETE FROM limits WHERE limit_id = ? AND tg_id = ?",
                (limit_id, tg_id)
            )
            await db.commit()
            return True
    except Exception as e:
        print(f"Error deleting limit: {e}")
        return False


async def get_limit_usage(tg_id: int, category: str, start_date: str, end_date: str) -> float:
    """Получение суммы расходов по категории за период"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            SELECT COALESCE(SUM(sum), 0) as total
            FROM transactions
            WHERE tg_id = ? 
            AND category = ?
            AND date_time BETWEEN ? AND ?
            AND type = 1
            """,
            (tg_id, category, start_date, end_date)
        )
        result = await cursor.fetchone()
        return float(result[0])


async def is_registered(tg_id: int) -> bool:
    """
    проверка, зарегистрирован ли пользователь.

    аргументы:
        tg_id (int): Telegram ID пользователя.

    возвращает:
        bool: True, если пользователь существует в базе и завершил регистрацию, False в противном случае.
    """
    user = await get_user(tg_id)

    # Проверяем наличие записи в базе и заполненность обязательных полей
    return bool(user and user.get('name') and user.get('total_sum') is not None)


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


async def check_limit_violation(tg_id: int, category: str, amount: float) -> Optional[Dict[str, Any]]:
    """
    Проверка нарушения лимита при добавлении новой транзакции.
    
    Возвращает информацию о нарушенном лимите или None, если лимиты не нарушены.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT * FROM limits 
            WHERE tg_id = ? 
            AND category = ? 
            AND date('now') BETWEEN start_date AND end_date
            """,
            (tg_id, category)
        )
        limit = await cursor.fetchone()
        
        if not limit:
            return None
            
        # Получаем сумму расходов за период лимита
        current_spent = await get_limit_usage(
            tg_id, 
            category, 
            limit["start_date"], 
            limit["end_date"]
        )
        
        # Проверяем, не будет ли превышен лимит после новой транзакции
        if current_spent + amount > limit["limit_sum"]:
            return {
                "category": category,
                "limit_sum": limit["limit_sum"],
                "current_spent": current_spent,
                "new_amount": amount,
                "end_date": limit["end_date"]
            }
        return None


async def get_expiring_limits() -> List[Dict[str, Any]]:
    """
    Получение списка лимитов, которые истекают завтра.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT l.*, u.tg_username 
            FROM limits l
            JOIN users u ON l.tg_id = u.tg_id
            WHERE l.end_date = date('now', '+1 day')
            """
        )
        return [dict(row) for row in await cursor.fetchall()]


async def get_violated_limits() -> List[Dict[str, Any]]:
    """
    Получение списка нарушенных лимитов (где текущие расходы превышают установленный лимит).
    """
    violated_limits = []
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT l.*, u.tg_username 
            FROM limits l
            JOIN users u ON l.tg_id = u.tg_id
            WHERE date('now') BETWEEN l.start_date AND l.end_date
            """
        )
        active_limits = await cursor.fetchall()
        
        for limit in active_limits:
            current_spent = await get_limit_usage(
                limit["tg_id"],
                limit["category"],
                limit["start_date"],
                limit["end_date"]
            )
            if current_spent > limit["limit_sum"]:
                limit_dict = dict(limit)
                limit_dict["current_spent"] = current_spent
                violated_limits.append(limit_dict)
                
        return violated_limits


async def get_transactions_by_category(tg_id: int, category: str, page: int = 0, items_per_page: int = 5) -> List[Dict[str, Any]]:
    """
    Получение списка транзакций пользователя по категории с поддержкой пагинации.

    Аргументы:
        tg_id (int): Telegram ID пользователя.
        category (str): Категория транзакций.
        page (int): Номер страницы (начиная с 0).
        items_per_page (int): Количество элементов на странице.

    Возвращает:
        List[Dict[str, Any]]: Список словарей с данными о транзакциях и общее количество транзакций.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        # Получаем общее количество транзакций для этой категории
        cursor = await db.execute(
            "SELECT COUNT(*) FROM transactions WHERE tg_id = ? AND category = ?",
            (tg_id, category)
        )
        total_count = (await cursor.fetchone())[0]

        # Получаем транзакции с пагинацией
        offset = page * items_per_page
        cursor = await db.execute(
            """
            SELECT transaction_id, date_time, type, description, category, sum 
            FROM transactions 
            WHERE tg_id = ? AND category = ? 
            ORDER BY date_time DESC
            LIMIT ? OFFSET ?
            """,
            (tg_id, category, items_per_page, offset)
        )
        rows = await cursor.fetchall()
        transactions = [
            {
                "transaction_id": row[0],
                "date_time": row[1],
                "type": row[2],
                "description": row[3],
                "category": row[4],
                "sum": row[5],
                "total_count": total_count
            }
            for row in rows
        ]
        return transactions
