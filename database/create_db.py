"""скрипт создания структуры базы данных с таблицами пользователей, транзакций и лимитов."""

import aiosqlite
import asyncio

async def create_database():
    # SQL-скрипт для создания базы
    schema: str = """
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
        AND json_extract(categories, '$') LIKE '%' || NEW.category || '%'
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
        AND json_extract(categories, '$') LIKE '%' || NEW.category || '%'
    );
END;
    """

    # Подключение и выполнение скрипта
    async with aiosqlite.connect("data.db") as db:
        await db.executescript(schema)
        await db.commit()
        print("База данных успешно создана!")

# Запуск создания базы
if __name__ == "__main__":
    asyncio.run(create_database())