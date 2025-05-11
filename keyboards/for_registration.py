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


async def get_category_continue_kb() -> types.ReplyKeyboardMarkup:
    kb = [
        [types.KeyboardButton(text="Да"), types.KeyboardButton(text="Отмена")]
    ]
    return types.ReplyKeyboardMarkup(
        keyboard=kb,
        resize_keyboard=True,
        one_time_keyboard=False)
