"""обработчик анализа финансов"""

import yaml
import os
import re
from datetime import datetime, timedelta
import asyncio
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from keyboards.for_analysys import get_period_kb, get_retry_kb
from database.db_methods import get_transactions_by_period, get_user, get_user_limits
from keyboards.for_start import get_menu_kb
from openai import AsyncOpenAI
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

router = Router()

# Загрузка сообщений из YAML с обработкой ошибок
MESSAGES_PATH = os.path.join(os.path.dirname(__file__), 'messages.yaml')
try:
    with open(MESSAGES_PATH, 'r', encoding='utf-8') as file:
        MESSAGES = yaml.safe_load(file)
    if MESSAGES is None:
        raise ValueError("messages.yaml is empty or invalid")
except FileNotFoundError:
    raise FileNotFoundError(f"Could not find messages.yaml at {MESSAGES_PATH}")
except Exception as e:
    raise Exception(f"Failed to load messages.yaml: {str(e)}")


# Определение состояний FSM
class AnalysisState(StatesGroup):
    select_period = State()
    view_analysis = State()


@router.message(Command('analysys'))
@router.message(F.text == 'Анализ [ИИ]')
async def cmd_analysys(message: types.Message, state: FSMContext):
    """Обработчик команды /analysys и кнопки 'Анализ'."""
    await message.answer(MESSAGES['analysys_emoji'], reply_markup=types.ReplyKeyboardRemove(),
                         disable_notification=True)
    await asyncio.sleep(0.5)
    await message.answer(MESSAGES['select_period'], reply_markup=await get_period_kb())
    await state.set_state(AnalysisState.select_period)


@router.callback_query(F.data == "analysys_back_to_menu")
async def handle_back_to_menu(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'Назад' для возврата в меню."""
    await callback.message.answer(MESSAGES['menu'], reply_markup=await get_menu_kb())
    await state.clear()
    await callback.answer()


@router.callback_query(F.data == "retry_analysys")
async def handle_retry_analysys(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'Повторить анализ'."""
    await callback.message.edit_text(MESSAGES['select_period'], reply_markup=await get_period_kb())
    await state.set_state(AnalysisState.select_period)
    await callback.answer()


@router.callback_query(AnalysisState.select_period)
async def process_period_selection(callback: types.CallbackQuery, state: FSMContext):
    """Обработка выбора периода для анализа."""
    await callback.answer()

    period = callback.data
    today = datetime.now().date()

    try:
        if period == '3_months':
            start_date = today - timedelta(days=90)
        elif period == '6_months':
            start_date = today - timedelta(days=180)
        elif period == '12_months':
            start_date = today - timedelta(days=365)
        else:
            await callback.message.answer(MESSAGES['invalid_period'])
            return

        end_date = today + timedelta(days=1)
        await state.update_data(period=period, start_date=start_date.isoformat(), end_date=end_date.isoformat())

        # Отправляем временное сообщение
        temp_message = await callback.message.answer(MESSAGES['loading'])
        await state.update_data(temp_message_id=temp_message.message_id)

        await show_analysis(callback, state)

    except Exception as e:
        try:
            temp_message_id = (await state.get_data()).get('temp_message_id')
            if temp_message_id:
                await callback.message.bot.edit_message_text(
                    text=MESSAGES['error_occurred'],
                    chat_id=callback.message.chat.id,
                    message_id=temp_message_id
                )
            else:
                await callback.message.answer(MESSAGES['error_occurred'])
        except Exception:
            await callback.message.answer(MESSAGES['error_occurred'])
        await state.set_state(AnalysisState.select_period)


async def fetch_deepseek_analysis(data: dict) -> str:
    """Запрос к DeepSeek API через OpenRouter."""
    client = AsyncOpenAI(
        api_key=OPENROUTER_API_KEY,
        base_url="https://openrouter.ai/api/v1"
    )

    try:
        # Формирование промпта для DeepSeek
        prompt = (
            "Ты финансовый аналитик. Проанализируй данные о доходах и расходах пользователя "
            "и дай рекомендации по оптимизации бюджета. Данные:\n"
            f"- Доход за период: {data['income']} руб.\n"
            f"- Общие расходы: {data['total_expenses']} руб.\n"
            f"- Расходы по категориям: {data['expenses_by_category']}.\n"
            f"- Период анализа: {data['period_months']} месяцев.\n\n"
            "Анализ:\n"
            "- Рассчитай средние месячные расходы по каждой категории\n"
            "- Укажи процент от общих расходов для каждой категории\n"
            "Рекомендации:\n"
            "- Если расходы по категории превышают 30% дохода, предложи сократить их\n"
            "- Если расходы превышают доходы, предложи общие меры экономии\n"
            "Верни ответ в структурированном виде без использования HTML, Markdown или любой другой разметки. "
            "Форматируй ответ только с помощью переносов строк. Пример формата:\n"
            "Анализ расходов:\n"
            "- Категория: сумма руб. (процент)\n"
            "...\n"
            "Рекомендации:\n"
            "- Мера 1\n"
            "- Мера 2\n"
        )

        response = await client.chat.completions.create(
            model="deepseek/deepseek-r1:free",
            messages=[
                {"role": "system",
                 "content": "Ты финансовый аналитик, предоставляющий точные рекомендации по управлению бюджетом."},
                {"role": "user", "content": prompt}
            ],
            stream=False
        )

        # Очистка ответа от любой разметки
        response_text = response.choices[0].message.content

        # Удаляем HTML-теги
        cleaned_text = re.sub(r'<.*?>', '', response_text)
        # Удаляем Markdown-символы (*, _, `, [], #)
        cleaned_text = re.sub(r'(\*|_|\`|#|\[.*?\]\(.*?\))', '', cleaned_text)
        # Заменяем \n на реальные переносы строк
        cleaned_text = cleaned_text.replace('\\n', '\n')

        return cleaned_text

    except Exception as e:
        return f"Ошибка при запросе к OpenRouter: {str(e)}"


async def show_analysis(callback: types.CallbackQuery, state: FSMContext):
    """Формирование и отправка анализа."""
    data = await state.get_data()
    tg_id = callback.from_user.id
    temp_message_id = data.get('temp_message_id')

    try:
        start_date = datetime.fromisoformat(data['start_date']).date()
        end_date = datetime.fromisoformat(data['end_date']).date()
        period = data['period']

        # Получение транзакций
        transactions = await get_transactions_by_period(tg_id, start_date.isoformat(), end_date.isoformat())

        # Расчет доходов и расходов по категориям
        income = sum(t['sum'] for t in transactions if t['type'] == 0)
        expenses = sum(t['sum'] for t in transactions if t['type'] == 1)
        expenses_by_category = {}
        for t in transactions:
            if t['type'] == 1:
                category = t['category'] or 'Без категории'
                expenses_by_category[category] = expenses_by_category.get(category, 0) + t['sum']

        # Проверяем наличие лимитов у пользователя
        user_limits = await get_user_limits(tg_id)

        # Подготовка данных для анализа
        analysis_data = {
            "income": income,
            "total_expenses": expenses,
            "expenses_by_category": expenses_by_category,
            "period_months": {"3_months": 3, "6_months": 6, "12_months": 12}[period],
            "has_limits": bool(user_limits)  # True если есть лимиты, False если нет
        }

        # Запрос анализа
        analysis_text = await fetch_deepseek_analysis(analysis_data)

        # Формирование текста ответа
        if analysis_text.startswith("Ошибка"):
            response_text = (
                    MESSAGES['analysis'].format(
                        period={"3_months": "3 месяца", "6_months": "6 месяцев", "12_months": "12 месяцев"}[period],
                        income=income,
                        expenses=expenses,
                        analysis=""
                    ) + f"Ошибка анализа:\n{analysis_text}"
            )
        else:
            response_text = MESSAGES['analysis'].format(
                period={"3_months": "3 месяца", "6_months": "6 месяцев", "12_months": "12 месяцев"}[period],
                income=income,
                expenses=expenses,
                analysis=analysis_text
            )

        # Редактируем временное сообщение
        await callback.message.bot.edit_message_text(
            text=response_text,
            chat_id=callback.message.chat.id,
            message_id=temp_message_id,
            reply_markup=await get_retry_kb()
        )

    except Exception as e:
        try:
            await callback.message.bot.edit_message_text(
                text=MESSAGES['error_occurred'],
                chat_id=callback.message.chat.id,
                message_id=temp_message_id
            )
        except Exception as e:
            print(f"Error editing message in show_analysis: {str(e)}")
            await callback.message.answer(MESSAGES['error_occurred'])

    await state.set_state(AnalysisState.view_analysis)