"""клавиатуры для проведения финансового прогноза и выбора периода"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


async def get_forecast_period_kb() -> InlineKeyboardMarkup:
    """создает клавиатуру для выбора периода прогноза (неделя, месяц, полгода, год) с опцией возврата."""
    buttons = [
        [
            InlineKeyboardButton(text="Неделя", callback_data="forecast_week"),
            InlineKeyboardButton(text="Месяц", callback_data="forecast_month")
        ],
        [
            InlineKeyboardButton(text="Полгода", callback_data="forecast_half_year"),
            InlineKeyboardButton(text="Год", callback_data="forecast_year")
        ],
        [InlineKeyboardButton(text="Назад ↩️", callback_data="forecast_back_to_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def get_forecast_retry_kb() -> InlineKeyboardMarkup:
    """создает клавиатуру с опциями повторного прогноза или возврата в главное меню."""
    buttons = [
        [InlineKeyboardButton(text="Новый прогноз 🔄", callback_data="retry_forecast")],
        [InlineKeyboardButton(text="Назад ↩️", callback_data="forecast_back_to_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons) 