"""клавиатуры для управления профилем и настройками пользователя"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


async def get_profile_kb() -> InlineKeyboardMarkup:
    """создает основную клавиатуру профиля с настройками и опцией возврата."""
    buttons = [
        [InlineKeyboardButton(text="Настройки", callback_data="settings")],
        [InlineKeyboardButton(text="↩️ Назад", callback_data="limit_back_to_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def get_settings_kb() -> InlineKeyboardMarkup:
    """создает клавиатуру настроек с опциями смены имени, сброса данных и информации."""
    buttons = [
        [InlineKeyboardButton(text="Сменить имя", callback_data="change_name")],
        [InlineKeyboardButton(text="Сброс данных", callback_data="reset_data")],
        [InlineKeyboardButton(text="О боте", callback_data="about_bot")],
        [InlineKeyboardButton(text="↩️ Назад", callback_data="back_profile")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def get_confirm_reset_kb() -> InlineKeyboardMarkup:
    """создает клавиатуру подтверждения сброса данных с опциями да/нет."""
    buttons = [
        [InlineKeyboardButton(text="Да, сбросить", callback_data="confirm_reset")],
        [InlineKeyboardButton(text="Нет, отменить", callback_data="back_settings")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def get_back_kb(action: str) -> InlineKeyboardMarkup:
    """создает универсальную клавиатуру с кнопкой возврата и настраиваемым действием."""
    buttons = [
        [InlineKeyboardButton(text="↩️ Назад", callback_data=f"back_{action}")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
