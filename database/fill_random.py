"""скрипт для заполнения базы данных тестовыми данными: пользователь, категории и транзакции"""

import aiosqlite
import asyncio
import random
import json
from datetime import datetime, timedelta

# Параметры
TG_ID = 813689840  # ID пользователя
NUM_TRANSACTIONS = 30  # Количество транзакций
NUM_CATEGORIES = 10  # Количество уникальных категорий
DB_PATH = "data.db"  # Путь к базе данных

# Список возможных категорий для случайного выбора
CATEGORY_POOL = [
    "еда", "транспорт", "одежда", "развлечения", "жилье", "здоровье",
    "образование", "подарки", "техника", "путешествия", "спорт", "книги",
    "косметика", "ремонт", "работа", "дом", "животные", "услуги", "инвестиции", "другое"
]


async def generate_random_transactions():
    """Заполняет базу случайными транзакциями для пользователя."""
    # Подключение к базе
    async with aiosqlite.connect(DB_PATH) as db:
        # Генерация уникальных категорий
        categories = random.sample(CATEGORY_POOL, NUM_CATEGORIES)
        categories_json = json.dumps(categories, ensure_ascii=False)  # Отключаем экранирование
        print(f"Создаваемые категории: {categories_json}")

        # Удаление существующего пользователя (и его транзакций через CASCADE)
        await db.execute("DELETE FROM users WHERE tg_id = ?", (TG_ID,))
        await db.commit()

        # Создание нового пользователя
        async with db.execute("""
            INSERT INTO users (tg_id, categories, tg_username, name, total_sum)
            VALUES (?, ?, ?, ?, ?)
        """, (TG_ID, categories_json, "golovach_0", None, 0.0)):
            await db.commit()

        # Проверка, что пользователь записан
        async with db.execute("SELECT categories FROM users WHERE tg_id = ?", (TG_ID,)) as cursor:
            user = await cursor.fetchone()
            if not user:
                print(f"Ошибка: Пользователь {TG_ID} не создан")
                return
            print(f"Категории пользователя в базе: {user[0]}")

        # Генерация случайных транзакций
        start_date = datetime(2023, 5, 15)
        end_date = datetime(2025, 5, 15)
        time_delta = end_date - start_date

        for i in range(NUM_TRANSACTIONS):
            # Случайная дата
            random_seconds = random.randint(0, int(time_delta.total_seconds()))
            random_date = start_date + timedelta(seconds=random_seconds)
            date_time = random_date.strftime("%Y-%m-%d %H:%M:%S")

            # Случайные данные
            trans_type = random.randint(0, 1)  # 0=доход, 1=расход
            description = f"Транзакция {i + 1}"
            category = random.choice(categories)
            amount = round(random.uniform(100, 10000), 2)

            # Вставка транзакции
            print(f"Вставка транзакции {i + 1}: category={category}, sum={amount}, date={date_time}")
            await db.execute("""
                INSERT INTO transactions (tg_id, date_time, type, description, category, sum)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (TG_ID, date_time, trans_type, description, category, amount))

        await db.commit()
        print(f"Добавлено {NUM_TRANSACTIONS} транзакций для пользователя {TG_ID} с {NUM_CATEGORIES} категориями")


# Запуск скрипта
if __name__ == "__main__":
    asyncio.run(generate_random_transactions())