from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


async def get_period_kb() -> InlineKeyboardMarkup:
    """Клавиатура для выбора периода анализа."""
    buttons = [
        [
            InlineKeyboardButton(text="3 месяца", callback_data="3_months"),
            InlineKeyboardButton(text="6 месяцев", callback_data="6_months")
        ],
        [InlineKeyboardButton(text="12 месяцев", callback_data="12_months")],
        [InlineKeyboardButton(text="Назад ↩️", callback_data="analysys_back_to_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def get_retry_kb() -> InlineKeyboardMarkup:
    """Клавиатура для повторного анализа или возврата в меню."""
    buttons = [
        [InlineKeyboardButton(text="Повторить анализ 🔄", callback_data="retry_analysys")],
        [InlineKeyboardButton(text="Назад ↩️", callback_data="analysys_back_to_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)