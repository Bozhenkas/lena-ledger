"""клавиатуры для управления лимитами расходов и их настройки"""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from math import ceil


def get_period_keyboard() -> InlineKeyboardMarkup:
    """создает клавиатуру для выбора периода лимита (дни, недели, месяцы, годы)."""
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="Дни", callback_data="period_days"),
        InlineKeyboardButton(text="Недели", callback_data="period_weeks"),
        InlineKeyboardButton(text="Месяцы", callback_data="period_months"),
        InlineKeyboardButton(text="Годы", callback_data="period_years")
    )
    builder.adjust(2, 2)
    return builder.as_markup()


def get_limit_actions_keyboard() -> InlineKeyboardMarkup:
    """создает клавиатуру с основными действиями управления лимитами (добавить, удалить, список, назад)."""
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(text="Добавить", callback_data="limit_add"),
        InlineKeyboardButton(text="Удалить", callback_data="limit_delete"),
        InlineKeyboardButton(text="Все лимиты", callback_data="limit_list"),
        InlineKeyboardButton(text="↩️ Назад", callback_data="limit_back_to_menu")
    )
    builder.adjust(2, 1, 1)
    return builder.as_markup()


def get_confirm_delete_keyboard(limit_id: int) -> InlineKeyboardMarkup:
    """создает клавиатуру подтверждения удаления лимита с опциями да/нет."""
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(
            text="Да",
            callback_data=f"confirm_delete_{limit_id}"
        ),
        InlineKeyboardButton(
            text="Нет",
            callback_data="cancel_delete"
        )
    )
    return builder.as_markup()


def get_limits_list_keyboard(limits: list) -> InlineKeyboardMarkup:
    """создает клавиатуру, отображающую все активные лимиты для выбора и удаления."""
    builder = InlineKeyboardBuilder()
    for limit in limits:
        text = f"{limit['category']}: {limit['limit_sum']}₽ до {limit['end_date']}"
        builder.add(InlineKeyboardButton(
            text=text,
            callback_data=f"delete_limit_{limit['limit_id']}"
        ))
    builder.adjust(1)
    return builder.as_markup()


async def get_categories_for_limits_kb(categories: list, page: int = 0) -> InlineKeyboardMarkup:
    """создает постраничную клавиатуру категорий специально для лимитов."""
    items_per_page = 5
    total_pages = ceil(len(categories) / items_per_page)

    start_idx = page * items_per_page
    end_idx = min(start_idx + items_per_page, len(categories))
    current_categories = categories[start_idx:end_idx]

    kb = []
    for i, category in enumerate(current_categories, start=start_idx):
        kb.append([InlineKeyboardButton(text=f"📊 {category}", callback_data=f"limit_category_{i}")])

    # Добавляем навигационные кнопки, если нужно
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text=f"⬅️ [{page + 1}/{total_pages}]", callback_data=f"limit_page_{page - 1}"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton(text=f"[{page + 1}/{total_pages}] ➡️", callback_data=f"limit_page_{page + 1}"))
    if nav_row:
        kb.append(nav_row)

    return InlineKeyboardMarkup(inline_keyboard=kb)
 