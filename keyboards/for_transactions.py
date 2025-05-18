"""клавиатуры для добавления и подтверждения финансовых транзакций"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


async def get_categories_kb(categories: list) -> InlineKeyboardMarkup:
    """создает клавиатуру, отображающую доступные категории для категоризации транзакции."""
    buttons = [
        [InlineKeyboardButton(text=category, callback_data=category)] for category in categories
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def get_confirm_kb() -> InlineKeyboardMarkup:
    """создает клавиатуру подтверждения с опциями подтверждения/отмены для одобрения транзакции."""
    buttons = [
        [InlineKeyboardButton(text="Подтвердить", callback_data="confirm")],
        [InlineKeyboardButton(text="Отменить", callback_data="cancel")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
