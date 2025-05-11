""""
создание клавиатуры ответа Главного меню
также используется как клавиатура для команды /start
"""

from aiogram import types


async def get_start_kb():
    k = [
        [types.KeyboardButton(text='Начать регистрацию'), ]
    ]
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=k,
        resize_keyboard=True,
        input_field_placeholder="Нажмите на кнопку",
        is_persistent=False,
        one_time_keyboard=True
    )
    return keyboard


async def get_menu_kb() -> types.ReplyKeyboardMarkup:
    kb = [
        [types.KeyboardButton(text="Потратил"), types.KeyboardButton(text="Получил")],
        [types.KeyboardButton(text="Анализ [β]")],
        [types.KeyboardButton(text="Категории"), types.KeyboardButton(text="Лимиты")],
        [types.KeyboardButton(text="Профиль")],

    ]
    return types.ReplyKeyboardMarkup(
        keyboard=kb,
        resize_keyboard=True,
        one_time_keyboard=False
    )
