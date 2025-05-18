"""клавиатуры для работы с категориями расходов и доходов"""

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from math import ceil


async def get_add_category_kb() -> ReplyKeyboardMarkup:
    """создает клавиатуру с опциями добавления новой категории или возврата в предыдущее меню."""
    kb = [
        [KeyboardButton(text="Добавить категорию")],
        [KeyboardButton(text="Назад ↩️")],
          ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


async def get_categories_kb(categories: list, page: int = 0) -> InlineKeyboardMarkup:
    """создает постраничную клавиатуру, отображающую категории с элементами навигации, по 5 элементов на странице."""
    items_per_page = 5
    total_pages = ceil(len(categories) / items_per_page)

    start_idx = page * items_per_page
    end_idx = min(start_idx + items_per_page, len(categories))
    current_categories = categories[start_idx:end_idx]

    kb = []
    for i, category in enumerate(current_categories, start=start_idx):
        kb.append([InlineKeyboardButton(text=f"📊 {category}", callback_data=f"category_{i}")])

    # Добавляем навигационные кнопки, если нужно
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text=f"⬅️ [{page + 1}/{total_pages}]", callback_data=f"page_{page - 1}"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton(text=f"[{page + 1}/{total_pages}] ➡️", callback_data=f"page_{page + 1}"))
    if nav_row:
        kb.append(nav_row)

    return InlineKeyboardMarkup(inline_keyboard=kb)


async def get_category_actions_kb(category_idx: int) -> InlineKeyboardMarkup:
    """создает клавиатуру с действиями для конкретной категории."""
    kb = [
        [
            InlineKeyboardButton(text="📋 Транзакции", callback_data=f"cat_trans_{category_idx}_0"),
            InlineKeyboardButton(text="🗑 Удалить", callback_data=f"cat_del_{category_idx}")
        ],
        [InlineKeyboardButton(text="↩️ К списку категорий", callback_data="back_to_categories")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


async def get_add_more_kb() -> ReplyKeyboardMarkup:
    """создает одноразовую клавиатуру с вопросом, хочет ли пользователь добавить еще одну категорию."""
    kb = [[KeyboardButton(text="Добавить ещё"), KeyboardButton(text="Хватит")]]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True, one_time_keyboard=True)
