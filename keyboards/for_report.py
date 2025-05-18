"""клавиатуры для формирования финансовых отчетов и навигации по периодам"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, timedelta


async def get_period_kb() -> InlineKeyboardMarkup:
    """создает клавиатуру для выбора периода отчета (день, неделя, месяц, полгода, год)."""
    buttons = [
        [
            InlineKeyboardButton(text="День", callback_data="day"),
            InlineKeyboardButton(text="Неделя", callback_data="week")
        ],
        [
            InlineKeyboardButton(text="Месяц", callback_data="month"),
            InlineKeyboardButton(text="Полгода", callback_data="half_year"),
            InlineKeyboardButton(text="Год", callback_data="year")
        ],
        [InlineKeyboardButton(text="Назад ↩️", callback_data="report_back_to_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def get_navigation_kb(period: str, start_date: str) -> InlineKeyboardMarkup:
    """создает навигационную клавиатуру с элементами управления для конкретного периода и форматированием дат."""
    buttons = []
    today = datetime.now().date()
    start_date = datetime.fromisoformat(start_date).date()
    # Словарь для русских названий месяцев (в нижнем регистре для декоративной кнопки)
    months = {
        1: 'января', 2: 'февраля', 3: 'марта', 4: 'апреля', 5: 'мая', 6: 'июня',
        7: 'июля', 8: 'августа', 9: 'сентября', 10: 'октября', 11: 'ноября', 12: 'декабря'
    }

    if period in ['day', 'week', 'month']:
        if period == 'day':
            prev_date = start_date - timedelta(days=1)
            if prev_date == today - timedelta(days=1):
                back_text = "Вчера"
            elif prev_date == today - timedelta(days=2):
                back_text = "Позавчера"
            else:
                back_text = f"{prev_date.day} {months[prev_date.month]}"
            # Кнопка "Вперед" для дня
            forward_text = ""
            show_forward = (period == 'day' and start_date < today)
            if show_forward:
                next_date = start_date + timedelta(days=1)
                if next_date == today:
                    forward_text = "Сегодня"
                elif next_date == today - timedelta(days=1):
                    forward_text = "Вчера"
                else:
                    forward_text = f"{next_date.day} {months[next_date.month]}"
            # Декоративная кнопка для дня
            decorate_text = f"[{start_date.day:02d}.{start_date.month:02d}]"
        elif period == 'week':
            back_text = "Предыдущая неделя"
            forward_text = "Следующая неделя"
            show_forward = (period == 'week' and start_date + timedelta(days=6) < today)
            # Декоративная кнопка для недели
            week_end = start_date + timedelta(days=6)
            decorate_text = f"[{start_date.day}.{start_date.month}-{week_end.day}.{week_end.month}]"
        else:  # month
            back_text = "Предыдущий месяц"
            forward_text = "Следующий месяц"
            show_forward = (period == 'month' and (start_date + timedelta(days=31)).replace(day=1) <= today)
            # Декоративная кнопка для месяца
            decorate_text = f"[{months[start_date.month]}]"

        # Добавляем кнопки "Назад", "Декоративная" и "Вперед" на одной строке
        navigation_buttons = []
        if show_forward:
            # Используем эмодзи, если есть обе кнопки
            navigation_buttons.append(InlineKeyboardButton(text="⬅️", callback_data="back"))
            navigation_buttons.append(InlineKeyboardButton(text=decorate_text, callback_data="decorate"))
            navigation_buttons.append(InlineKeyboardButton(text="➡️", callback_data="forward"))
        else:
            # Оставляем текст, если только одна кнопка
            navigation_buttons.append(InlineKeyboardButton(text=back_text, callback_data="back"))
        buttons.append(navigation_buttons)

    # Кнопка "Назад к выбору периода"
    buttons.append([InlineKeyboardButton(text="Назад ↩️", callback_data="select_period")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)
