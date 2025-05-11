from aiogram.client.default import DefaultBotProperties
from aiogram import Bot, Dispatcher

# del
from aiogram import Router, types, F
from aiogram.filters.command import Command
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest
# del

from handlers import start, registration, categories
import asyncio
from dotenv import load_dotenv
import os

# загрузка переменных из .env
load_dotenv()

# получение токена из переменной окружения
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")

# отладочный вывод для проверки
print("TELEGRAM_TOKEN:", BOT_TOKEN)
print("Current working directory:", os.getcwd())

# проверка токена
if not BOT_TOKEN:
    raise ValueError("токен не найден в .env")

# настройка бота и диспетчера с глобальным parse_mode
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode='HTML'))
dp = Dispatcher()

# регистрация роутеров
dp.include_routers(start.router, registration.router, categories.router)


async def main():
    # запуск бота
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
