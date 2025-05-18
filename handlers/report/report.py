"""обработчик формирования финансовых отчетов за выбранный период времени"""

import yaml
import os
from datetime import datetime, timedelta
import asyncio

from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from keyboards.for_report import get_period_kb, get_navigation_kb
from database.db_methods import get_transactions_by_period, get_user
from keyboards.for_start import get_menu_kb

router = Router()

# Загрузка сообщений из YAML
MESSAGES_PATH = os.path.join(os.path.dirname(__file__), 'messages.yaml')
with open(MESSAGES_PATH, 'r', encoding='utf-8') as file:
    MESSAGES = yaml.safe_load(file)


# Определение состояний FSM
class ReportState(StatesGroup):
    select_period = State()
    view_report = State()


@router.message(Command('report'))
@router.message(F.text == 'Отчёт')
async def cmd_report(message: types.Message, state: FSMContext):
    """Обработчик команды /report и кнопки 'Отчёт'."""
    await message.answer(MESSAGES['report_emoji'], reply_markup=types.ReplyKeyboardRemove(), disable_notification=True)
    await asyncio.sleep(0.5)
    await message.answer(MESSAGES['select_period'], reply_markup=await get_period_kb())
    await state.set_state(ReportState.select_period)


@router.callback_query(F.data == "report_back_to_menu")
async def handle_back_to_menu(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'Назад' для возврата в меню."""
    await callback.message.answer(MESSAGES['menu'], reply_markup=await get_menu_kb())
    await state.clear()
    await callback.answer()  # Закрываем callback


@router.callback_query(F.data == "decorate")
async def handle_decorate(callback: types.CallbackQuery):
    """Обработчик декоративной кнопки."""
    await callback.answer("Это декоративная кнопка")


@router.callback_query(ReportState.select_period)
async def process_period_selection(callback: types.CallbackQuery, state: FSMContext):
    """Обработка выбора периода."""
    period = callback.data
    today = datetime.now().date()

    if period == 'day':
        start_date = today
        end_date = today + timedelta(days=1)
    elif period == 'week':
        start_date = today - timedelta(days=today.weekday())  # Начало недели (понедельник)
        end_date = start_date + timedelta(days=7)
    elif period == 'month':
        start_date = today.replace(day=1)  # Начало месяца
        end_date = (start_date + timedelta(days=32)).replace(day=1)
    elif period == 'half_year':
        start_date = today - timedelta(days=180)
        end_date = today + timedelta(days=1)
    elif period == 'year':
        start_date = today.replace(month=1, day=1)  # Начало года
        end_date = today.replace(month=12, day=31) + timedelta(days=1)
    else:
        await callback.answer('Неверный период')
        return

    await state.update_data(period=period, start_date=start_date.isoformat(), end_date=end_date.isoformat())
    await show_report(callback, state)
    await callback.answer()  # Закрываем callback


def get_period_display(period: str, start_date: datetime.date, today: datetime.date) -> str:
    """Генерация человекочитаемого названия периода."""
    # Словарь для русских названий месяцев
    months = {
        1: 'января', 2: 'февраля', 3: 'марта', 4: 'апреля', 5: 'мая', 6: 'июня',
        7: 'июля', 8: 'августа', 9: 'сентября', 10: 'октября', 11: 'ноября', 12: 'декабря'
    }

    if period == 'day':
        if start_date == today:
            return "сегодня"
        elif start_date == today - timedelta(days=1):
            return "вчера"
        elif start_date == today - timedelta(days=2):
            return "позавчера"
        else:
            return f"{start_date.day} {months[start_date.month]}"
    elif period == 'week':
        week_end = start_date + timedelta(days=6)  # Конец недели
        if start_date <= today <= week_end:
            return "эта неделя"
        else:
            return f"неделя с {start_date.day} {months[start_date.month]} по {week_end.day} {months[week_end.month]}"
    elif period == 'month':
        month_end = (start_date + timedelta(days=31)).replace(day=1) - timedelta(days=1)  # Последний день месяца
        if start_date.month == today.month and start_date.year == today.year:
            return "этот месяц"
        else:
            return f"с 1 {months[start_date.month]} по {month_end.day} {months[month_end.month]} {start_date.year}"
    elif period == 'half_year':
        return "последние полгода"
    elif period == 'year':
        if start_date.year == today.year:
            return "этот год"
        else:
            return f"{start_date.year} год"
    return period


async def show_report(callback: types.CallbackQuery, state: FSMContext):
    """Формирование и отправка отчета."""
    data = await state.get_data()
    tg_id = callback.from_user.id
    start_date = datetime.fromisoformat(data['start_date']).date()
    end_date = datetime.fromisoformat(data['end_date']).date()
    period = data['period']
    today = datetime.now().date()

    # Получение транзакций до конца выбранного периода
    transactions = await get_transactions_by_period(tg_id, "2000-01-01", end_date.isoformat())

    # Расчет баланса на конец периода
    total_sum = 0
    for t in transactions:
        if t['type'] == 0:  # доход
            total_sum += t['sum']
        else:  # расход
            total_sum -= t['sum']

    # Получение транзакций только за выбранный период для отчета
    period_transactions = [t for t in transactions if datetime.fromisoformat(t['date_time']).date() >= start_date]

    # Расчет доходов и расходов за период
    income = sum(t['sum'] for t in period_transactions if t['type'] == 0)
    expenses = sum(t['sum'] for t in period_transactions if t['type'] == 1)
    expenses_by_category = {}
    for t in period_transactions:
        if t['type'] == 1:
            category = t['category'] or 'Без категории'
            expenses_by_category[category] = expenses_by_category.get(category, 0) + t['sum']

    # Генерация человекочитаемого названия периода
    period_display = get_period_display(period, start_date, today)

    # Формирование текста отчета
    expenses_text = '\n'.join([f"{cat}: {sum} р." for cat, sum in expenses_by_category.items()]) or "Нет расходов"
    report_text = MESSAGES['report'].format(
        period=period_display,
        income=income,
        expenses=expenses,
        expenses_by_category=expenses_text,
        remaining_income=income - expenses,
        total_sum=total_sum
    )

    # Отправка отчета с клавиатурой навигации
    keyboard = await get_navigation_kb(period, start_date.isoformat())
    await callback.message.edit_text(report_text, reply_markup=keyboard)
    await state.set_state(ReportState.view_report)
    await callback.answer()  # Закрываем callback


@router.callback_query(ReportState.view_report)
async def process_navigation(callback: types.CallbackQuery, state: FSMContext):
    """Обработка навигации по периодам."""
    action = callback.data
    if action == 'select_period':
        await callback.message.edit_text(MESSAGES['select_period'], reply_markup=await get_period_kb())
        await state.set_state(ReportState.select_period)
        await callback.answer()  # Закрываем callback
        return

    data = await state.get_data()
    period = data['period']
    start_date = datetime.fromisoformat(data['start_date']).date()

    if action == 'back':
        if period == 'day':
            start_date -= timedelta(days=1)
        elif period == 'week':
            start_date -= timedelta(days=7)
        elif period == 'month':
            start_date = (start_date - timedelta(days=1)).replace(day=1)
    elif action == 'forward':
        if period == 'day':
            start_date += timedelta(days=1)
        elif period == 'week':
            start_date += timedelta(days=7)
        elif period == 'month':
            start_date = (start_date + timedelta(days=32)).replace(day=1)

    # Пересчет конечной даты
    if period == 'day':
        end_date = start_date + timedelta(days=1)
    elif period == 'week':
        end_date = start_date + timedelta(days=7)
    elif period == 'month':
        end_date = (start_date + timedelta(days=32)).replace(day=1)
    else:
        end_date = start_date

    await state.update_data(start_date=start_date.isoformat(), end_date=end_date.isoformat())
    await show_report(callback, state)
    await callback.answer()  # Закрываем callback