from aiogram import types


async def get_confirm_kb() -> types.ReplyKeyboardMarkup:
    kb = [
        [types.KeyboardButton(text="Да"), types.KeyboardButton(text="Нет")]
    ]
    return types.ReplyKeyboardMarkup(
        keyboard=kb,
        resize_keyboard=True,
        one_time_keyboard=False
    )


async def get_add_category_kb() -> types.ReplyKeyboardMarkup:
    kb = [
        [types.KeyboardButton(text="Добавить категории")]
    ]
    return types.ReplyKeyboardMarkup(
        keyboard=kb,
        resize_keyboard=True,
        one_time_keyboard=False
    )