"""Скрипт для заполнения базы данных тестовыми данными с сохранением существующих данных"""

import aiosqlite
import asyncio
import json
import random
from datetime import datetime, timedelta
from typing import List, Dict, Optional

# Конфигурация
DB_PATH = "data.db"  # База данных находится в той же директории, что и скрипт
TG_ID = 294057781  # ID пользователя для тестовых данных

# Настройки генерации данных
NUM_TRANSACTIONS = 25  # Сколько транзакций генерировать
MIN_AMOUNT = 100  # Минимальная сумма транзакции
MAX_AMOUNT = 10000  # Максимальная сумма транзакции
DAYS_BACK = 60  # За сколько дней генерировать транзакции

# Пул возможных категорий для добавления
AVAILABLE_CATEGORIES = [
    "продукты", "кафе", "транспорт", "такси", "развлечения",
    "одежда", "техника", "здоровье", "спорт", "подарки",
    "путешествия", "образование", "дом", "красота", "хобби"
]

async def get_user_data(db: aiosqlite.Connection, tg_id: int) -> Optional[Dict]:
    """Получение данных пользователя из БД"""
    async with db.execute(
        "SELECT tg_id, categories, name, total_sum FROM users WHERE tg_id = ?",
        (tg_id,)
    ) as cursor:
        row = await cursor.fetchone()
        if row:
            return {
                "tg_id": row[0],
                "categories": json.loads(row[1]) if row[1] else [],
                "name": row[2],
                "total_sum": row[3] or 0.0
            }
        return None

async def update_user_categories(
    db: aiosqlite.Connection,
    tg_id: int,
    current_categories: List[str]
) -> List[str]:
    """Обновление категорий пользователя, добавление новых случайных категорий"""
    # Находим категории, которых еще нет у пользователя
    new_categories = [cat for cat in AVAILABLE_CATEGORIES if cat not in current_categories]
    
    if new_categories:
        # Добавляем от 2 до 4 новых случайных категорий
        num_new_categories = min(random.randint(2, 4), len(new_categories))
        selected_new_categories = random.sample(new_categories, num_new_categories)
        
        # Объединяем текущие и новые категории
        updated_categories = current_categories + selected_new_categories
        
        # Сохраняем обновленный список категорий в БД
        categories_json = json.dumps(updated_categories, ensure_ascii=False)
        await db.execute(
            "UPDATE users SET categories = ? WHERE tg_id = ?",
            (categories_json, tg_id)
        )
        await db.commit()
        
        print(f"Добавлены новые категории: {selected_new_categories}")
        return updated_categories
    
    print("Новые категории не добавлены")
    return current_categories

async def generate_random_transactions(
    db: aiosqlite.Connection,
    tg_id: int,
    categories: List[str],
    num_transactions: int
) -> None:
    """Генерация случайных транзакций"""
    # Определяем временной период
    end_date = datetime.now()
    start_date = end_date - timedelta(days=DAYS_BACK)
    time_delta = end_date - start_date
    
    # Счетчики для статистики
    added_transactions = 0
    total_income = 0
    total_expenses = 0
    
    for i in range(num_transactions):
        try:
            # Генерируем случайную дату
            random_seconds = random.randint(0, int(time_delta.total_seconds()))
            transaction_date = start_date + timedelta(seconds=random_seconds)
            date_time = transaction_date.strftime("%Y-%m-%d %H:%M:%S")
            
            # Генерируем данные транзакции
            trans_type = random.randint(0, 1)  # 0=доход, 1=расход
            amount = round(random.uniform(MIN_AMOUNT, MAX_AMOUNT), 2)
            
            # Для расходов указываем категорию, для доходов - нет
            category = random.choice(categories) if trans_type == 1 else None
            description = (
                f"Тестовый доход {i+1}" if trans_type == 0
                else f"Тестовый расход {i+1} - {category}"
            )
            
            # Добавляем транзакцию
            await db.execute("""
                INSERT INTO transactions (tg_id, date_time, type, description, category, sum)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (tg_id, date_time, trans_type, description, category, amount))
            
            # Обновляем счетчики
            added_transactions += 1
            if trans_type == 0:
                total_income += amount
            else:
                total_expenses += amount
                
            print(f"Добавлена транзакция: тип={'доход' if trans_type == 0 else 'расход'}, "
                  f"сумма={amount:.2f}, категория={category or 'нет'}, дата={date_time}")
            
        except Exception as e:
            print(f"Ошибка при добавлении транзакции {i+1}: {str(e)}")
            continue
    
    await db.commit()
    
    # Выводим итоговую статистику
    print(f"\nИтоги генерации данных:")
    print(f"Добавлено транзакций: {added_transactions}")
    print(f"Общий доход: {total_income:.2f} руб.")
    print(f"Общие расходы: {total_expenses:.2f} руб.")
    print(f"Баланс за период: {(total_income - total_expenses):.2f} руб.")

async def main():
    """Основная функция скрипта"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            # Получаем данные пользователя
            user_data = await get_user_data(db, TG_ID)
            if not user_data:
                print(f"Ошибка: пользователь {TG_ID} не найден в базе")
                return
                
            print(f"\nТекущие данные пользователя:")
            print(f"Имя: {user_data['name']}")
            print(f"Баланс: {user_data['total_sum']:.2f} руб.")
            print(f"Категории: {user_data['categories']}")
            
            # Обновляем категории пользователя
            updated_categories = await update_user_categories(
                db, TG_ID, user_data['categories']
            )
            
            # Генерируем новые транзакции
            print(f"\nНачинаем генерацию {NUM_TRANSACTIONS} транзакций...")
            await generate_random_transactions(
                db, TG_ID, updated_categories, NUM_TRANSACTIONS
            )
            
    except Exception as e:
        print(f"Произошла ошибка: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())