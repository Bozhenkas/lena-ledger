from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from math import ceil


async def get_add_category_kb() -> ReplyKeyboardMarkup:
    """Клавиатура для добавления категории."""
    kb = [
        [KeyboardButton(text="Добавить категории")],
        [KeyboardButton(text="Назад ↩️")],
          ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


async def get_categories_kb(categories: list, page: int) -> InlineKeyboardMarkup:
    """Инлайн-клавиатура с категориями (до 5 за раз) и пагинацией."""
    items_per_page = 5
    total_pages = ceil(len(categories) / items_per_page)

    start_idx = page * items_per_page
    end_idx = min(start_idx + items_per_page, len(categories))
    current_categories = categories[start_idx:end_idx]

    kb = []
    for i, category in enumerate(current_categories, start=start_idx):
        kb.append([InlineKeyboardButton(text=category, callback_data=f"category_{i}")])

    # Добавляем навигационные кнопки, если нужно
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"page_{page - 1}"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton(text="Вперед ➡️", callback_data=f"page_{page + 1}"))
    if nav_row:
        kb.append(nav_row)

    return InlineKeyboardMarkup(inline_keyboard=kb)


async def get_add_more_kb() -> ReplyKeyboardMarkup:
    """Клавиатура для вопроса о добавлении ещё одной категории."""
    kb = [[KeyboardButton(text="Добавить ещё"), KeyboardButton(text="Хватит")]]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True, one_time_keyboard=True)
