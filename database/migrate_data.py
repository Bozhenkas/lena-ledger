"""Скрипт для миграции данных из резервной копии в новую базу данных"""

import asyncio
import aiosqlite
import json
from datetime import datetime

# SQL-скрипт для создания структуры базы данных
SCHEMA = """
-- Таблица пользователей
CREATE TABLE users (
    tg_id INTEGER PRIMARY KEY,
    categories TEXT,
    tg_username TEXT,
    name TEXT,
    total_sum REAL DEFAULT 0.0
);

-- Таблица транзакций
CREATE TABLE transactions (
    transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
    tg_id INTEGER,
    date_time TEXT NOT NULL,
    type INTEGER NOT NULL,
    description TEXT,
    category TEXT,
    sum REAL NOT NULL CHECK (sum >= 0),
    FOREIGN KEY (tg_id) REFERENCES users(tg_id) ON DELETE CASCADE
);
CREATE INDEX idx_transactions_tg_id ON transactions(tg_id);
CREATE INDEX idx_transactions_date_time ON transactions(date_time);

-- Таблица лимитов
CREATE TABLE limits (
    limit_id INTEGER PRIMARY KEY AUTOINCREMENT,
    tg_id INTEGER,
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    category TEXT,
    limit_sum REAL NOT NULL CHECK (limit_sum >= 0),
    FOREIGN KEY (tg_id) REFERENCES users(tg_id) ON DELETE CASCADE
);
CREATE INDEX idx_limits_tg_id ON limits(tg_id);
CREATE INDEX idx_limits_dates ON limits(start_date, end_date);

-- Триггеры для total_sum
CREATE TRIGGER update_total_sum_after_insert
AFTER INSERT ON transactions
BEGIN
    UPDATE users
    SET total_sum = total_sum + 
        CASE NEW.type 
            WHEN 0 THEN NEW.sum 
            WHEN 1 THEN -NEW.sum 
        END
    WHERE tg_id = NEW.tg_id;
END;

CREATE TRIGGER update_total_sum_after_delete
AFTER DELETE ON transactions
BEGIN
    UPDATE users
    SET total_sum = total_sum - 
        CASE OLD.type 
            WHEN 0 THEN OLD.sum 
            WHEN 1 THEN -OLD.sum 
        END
    WHERE tg_id = OLD.tg_id;
END;

CREATE TRIGGER update_total_sum_after_update
AFTER UPDATE ON transactions
BEGIN
    UPDATE users
    SET total_sum = total_sum - 
        CASE OLD.type 
            WHEN 0 THEN OLD.sum 
            WHEN 1 THEN -OLD.sum 
        END + 
        CASE NEW.type 
            WHEN 0 THEN NEW.sum 
            WHEN 1 THEN -NEW.sum 
        END
    WHERE tg_id = NEW.tg_id;
END;

-- Триггеры для проверки категорий
CREATE TRIGGER check_transaction_category
BEFORE INSERT ON transactions
WHEN NEW.category IS NOT NULL
BEGIN
    SELECT RAISE(ABORT, 'Category not found in user categories')
    WHERE NOT EXISTS (
        SELECT 1
        FROM users
        WHERE tg_id = NEW.tg_id
        AND json_array_length(json_extract(categories, '$')) > 0
        AND EXISTS (
            SELECT 1
            FROM json_each(categories)
            WHERE value = NEW.category
        )
    );
END;

CREATE TRIGGER check_limit_category
BEFORE INSERT ON limits
WHEN NEW.category IS NOT NULL
BEGIN
    SELECT RAISE(ABORT, 'Category not found in user categories')
    WHERE NOT EXISTS (
        SELECT 1
        FROM users
        WHERE tg_id = NEW.tg_id
        AND json_array_length(json_extract(categories, '$')) > 0
        AND EXISTS (
            SELECT 1
            FROM json_each(categories)
            WHERE value = NEW.category
        )
    );
END;
"""

async def migrate_data():
    try:
        # Подключаемся к старой базе
        async with aiosqlite.connect('database/data.db.backup') as old_db:
            old_db.row_factory = aiosqlite.Row
            
            # Получаем данные пользователей
            async with old_db.execute("SELECT * FROM users") as cursor:
                users = await cursor.fetchall()
            
            # Получаем транзакции
            async with old_db.execute("SELECT * FROM transactions") as cursor:
                transactions = await cursor.fetchall()
            
            # Получаем лимиты
            async with old_db.execute("SELECT * FROM limits") as cursor:
                limits = await cursor.fetchall()
        
        # Подключаемся к новой базе
        async with aiosqlite.connect('database/data.db') as new_db:
            # Создаем таблицы
            await new_db.executescript(SCHEMA)
            
            # Мигрируем пользователей
            for user in users:
                await new_db.execute(
                    "INSERT INTO users (tg_id, categories, tg_username, name, total_sum) VALUES (?, ?, ?, ?, ?)",
                    (user['tg_id'], user['categories'], user['tg_username'], user['name'], user['total_sum'])
                )
            
            # Мигрируем транзакции
            for trans in transactions:
                await new_db.execute(
                    """INSERT INTO transactions 
                    (transaction_id, tg_id, date_time, type, description, category, sum) 
                    VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (trans['transaction_id'], trans['tg_id'], trans['date_time'], 
                     trans['type'], trans['description'], trans['category'], trans['sum'])
                )
            
            # Мигрируем лимиты
            for limit in limits:
                await new_db.execute(
                    """INSERT INTO limits 
                    (limit_id, tg_id, start_date, end_date, category, limit_sum) 
                    VALUES (?, ?, ?, ?, ?, ?)""",
                    (limit['limit_id'], limit['tg_id'], limit['start_date'], 
                     limit['end_date'], limit['category'], limit['limit_sum'])
                )
            
            await new_db.commit()
            print("Миграция данных успешно завершена!")
            
    except Exception as e:
        print(f"Ошибка при миграции данных: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(migrate_data()) 