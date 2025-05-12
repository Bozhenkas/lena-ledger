from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

async def get_profile_kb(message_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для профиля."""
    buttons = [
        [InlineKeyboardButton(text="Настройки", callback_data="settings")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"back_main_{message_id}")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

async def get_settings_kb() -> InlineKeyboardMarkup:
    """Клавиатура для настроек."""
    buttons = [
        [InlineKeyboardButton(text="Сменить имя", callback_data="change_name")],
        [InlineKeyboardButton(text="Сброс данных", callback_data="reset_data")],
        [InlineKeyboardButton(text="О боте", callback_data="about_bot")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_profile")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

async def get_confirm_reset_kb() -> InlineKeyboardMarkup:
    """Клавиатура для подтверждения сброса данных."""
    buttons = [
        [InlineKeyboardButton(text="Да, сбросить", callback_data="confirm_reset")],
        [InlineKeyboardButton(text="Нет, отменить", callback_data="back_settings")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

async def get_back_kb(action: str) -> InlineKeyboardMarkup:
    """Универсальная клавиатура для кнопки 'Назад'."""
    buttons = [
        [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"back_{action}")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)