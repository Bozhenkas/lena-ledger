"""клавиатуры для добавления и подтверждения финансовых транзакций"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


async def get_categories_kb(categories: list) -> InlineKeyboardMarkup:
    """создает клавиатуру, отображающую доступные категории для категоризации транзакции."""
    buttons = []
    for i, category in enumerate(categories):
        buttons.append([
            InlineKeyboardButton(
                text=f"📊 {category}",
                callback_data=f"trans_cat_{i}"
            )
        ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def get_confirm_kb() -> InlineKeyboardMarkup:
    """создает клавиатуру для подтверждения или отмены транзакции."""
    buttons = [
        [
            InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm"),
            InlineKeyboardButton(text="❌ Отменить", callback_data="cancel")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
