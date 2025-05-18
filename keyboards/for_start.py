"""клавиатуры для главного меню и начальной регистрации пользователя"""

from aiogram import types


async def get_start_kb():
    """создает одноразовую клавиатуру для начальной регистрации с одной кнопкой."""
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
    """создает клавиатуру главного меню со всеми основными функциями бота и опциями навигации."""
    kb = [
        [types.KeyboardButton(text="Потратил"), types.KeyboardButton(text="Получил")],
        [types.KeyboardButton(text="Отчёт"), types.KeyboardButton(text="Анализ [ИИ]"),
         types.KeyboardButton(text="Прогноз [ИИ]")],
        [types.KeyboardButton(text="Категории"), types.KeyboardButton(text="Лимиты")],
        [types.KeyboardButton(text="Профиль")],

    ]
    return types.ReplyKeyboardMarkup(
        keyboard=kb,
        resize_keyboard=True,
        is_persistent=True,
        one_time_keyboard=False
    )
