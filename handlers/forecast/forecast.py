"""обработчик прогноза финансов"""

import yaml
import os
import re
from datetime import datetime, timedelta
import asyncio
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from keyboards.for_forecast import get_forecast_period_kb, get_forecast_retry_kb
from database.db_methods import get_transactions_by_period, get_user
from keyboards.for_start import get_menu_kb
from openai import AsyncOpenAI
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()
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
class ForecastState(StatesGroup):
    select_period = State()
    view_forecast = State()


@router.message(Command('forecast'))
@router.message(F.text == 'Прогноз [ИИ]')
async def cmd_forecast(message: types.Message, state: FSMContext):
    """Обработчик команды /forecast и кнопки 'Прогноз [ИИ]'."""
    await message.answer(MESSAGES['forecast_emoji'], reply_markup=types.ReplyKeyboardRemove(),
                        disable_notification=True)
    await asyncio.sleep(0.5)
    await message.answer(MESSAGES['select_period'], reply_markup=await get_forecast_period_kb())
    await state.set_state(ForecastState.select_period)


@router.callback_query(F.data == "forecast_back_to_menu")
async def handle_back_to_menu(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'Назад' для возврата в меню."""
    await callback.message.answer(MESSAGES['menu'], reply_markup=await get_menu_kb())
    await state.clear()
    await callback.answer()


@router.callback_query(F.data == "retry_forecast")
async def handle_retry_forecast(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'Новый прогноз'."""
    await callback.message.edit_text(MESSAGES['select_period'], reply_markup=await get_forecast_period_kb())
    await state.set_state(ForecastState.select_period)
    await callback.answer()


@router.callback_query(ForecastState.select_period)
async def process_period_selection(callback: types.CallbackQuery, state: FSMContext):
    """Обработка выбора периода для прогноза."""
    await callback.answer()

    period = callback.data
    today = datetime.now().date()

    try:
        # Определяем период для анализа (3 месяца назад) и период прогноза
        start_date = today - timedelta(days=90)  # Всегда анализируем последние 3 месяца
        end_date = today + timedelta(days=1)
        
        forecast_periods = {
            "forecast_week": ("неделю", 7),
            "forecast_month": ("месяц", 30),
            "forecast_half_year": ("полгода", 180),
            "forecast_year": ("год", 365)
        }
        
        if period not in forecast_periods:
            await callback.message.answer(MESSAGES['invalid_period'])
            return

        forecast_name, forecast_days = forecast_periods[period]
        await state.update_data(
            period=period,
            forecast_name=forecast_name,
            forecast_days=forecast_days,
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat()
        )

        # Отправляем временное сообщение
        temp_message = await callback.message.answer(MESSAGES['loading'])
        await state.update_data(temp_message_id=temp_message.message_id)

        await show_forecast(callback, state)

    except Exception as e:
        print(f"Error in process_period_selection: {str(e)}")
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
        except Exception as e:
            print(f"Error editing message in process_period_selection: {str(e)}")
            await callback.message.answer(MESSAGES['error_occurred'])
        await state.set_state(ForecastState.select_period)


async def fetch_forecast(data: dict) -> str:
    """Запрос к DeepSeek API через OpenRouter."""
    client = AsyncOpenAI(
        api_key=OPENROUTER_API_KEY,
        base_url="https://openrouter.ai/api/v1"
    )

    try:
        # Формирование промпта для DeepSeek
        prompt = (
            "Ты финансовый аналитик. Сделай прогноз расходов на будущий период на основе текущих данных. Данные:\n"
            f"- Доход за последние 3 месяца: {data['income']} руб.\n"
            f"- Общие расходы за 3 месяца: {data['total_expenses']} руб.\n"
            f"- Расходы по категориям за 3 месяца: {data['expenses_by_category']}.\n"
            f"- Период прогноза: {data['forecast_name']}\n"
            f"- Длительность прогноза: {data['forecast_days']} дней\n\n"
            "Сделай прогноз, который включает:\n"
            "1. Прогноз расходов по каждой категории:\n"
            "   - Учитывай сезонность (если период больше месяца)\n"
            "   - Учитывай инфляцию (5% годовых)\n"
            "   - Рассчитай месячные/дневные средние значения\n"
            "2. Общий прогноз:\n"
            "   - Предполагаемая общая сумма расходов за период\n"
            "   - Ожидаемое соотношение с доходами\n"
            "3. Риски и рекомендации:\n"
            "   - Возможные превышения лимитов\n"
            "   - Категории с потенциальным ростом расходов\n"
            "   - Советы по подготовке к будущим расходам\n\n"
            "Верни ответ в структурированном виде без использования HTML, Markdown или любой другой разметки. "
            "Форматируй ответ только с помощью переносов строк. Пример формата:\n"
            f"Прогноз на {data['forecast_name']}:\n"
            "- Категория: прогноз руб. (обоснование)\n"
            "...\n"
            "Общий прогноз:\n"
            "- Общая сумма: руб.\n"
            "- Среднемесячные расходы: руб.\n"
            "\n"
            "Риски и рекомендации:\n"
            "- Риск 1\n"
            "- Рекомендация 1\n"
        )

        response = await client.chat.completions.create(
            model="deepseek/deepseek-r1:free",
            messages=[
                {"role": "system",
                 "content": "Ты финансовый аналитик, специализирующийся на прогнозировании расходов. Твои прогнозы основаны на анализе исторических данных, сезонности и экономических факторов."},
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


async def show_forecast(callback: types.CallbackQuery, state: FSMContext):
    """Формирование и отправка прогноза."""
    data = await state.get_data()
    tg_id = callback.from_user.id
    temp_message_id = data.get('temp_message_id')

    try:
        start_date = datetime.fromisoformat(data['start_date']).date()
        end_date = datetime.fromisoformat(data['end_date']).date()
        forecast_name = data['forecast_name']

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

        # Подготовка данных для прогноза
        forecast_data = {
            "income": income,
            "total_expenses": expenses,
            "expenses_by_category": expenses_by_category,
            "forecast_name": forecast_name,
            "forecast_days": data['forecast_days']
        }

        # Запрос прогноза
        forecast_text = await fetch_forecast(forecast_data)

        # Формирование текста ответа
        if forecast_text.startswith("Ошибка"):
            response_text = (
                    MESSAGES['forecast'].format(
                        period=forecast_name,
                        income=income,
                        expenses=expenses,
                        forecast=""
                    ) + f"Ошибка прогноза:\n{forecast_text}"
            )
        else:
            response_text = MESSAGES['forecast'].format(
                period=forecast_name,
                income=income,
                expenses=expenses,
                forecast=forecast_text
            )

        # Редактируем временное сообщение
        await callback.message.bot.edit_message_text(
            text=response_text,
            chat_id=callback.message.chat.id,
            message_id=temp_message_id,
            reply_markup=await get_forecast_retry_kb()
        )

    except Exception as e:
        print(f"Error in show_forecast: {str(e)}")
        try:
            await callback.message.bot.edit_message_text(
                text=MESSAGES['error_occurred'],
                chat_id=callback.message.chat.id,
                message_id=temp_message_id
            )
        except Exception as e:
            print(f"Error editing message in show_forecast: {str(e)}")
            await callback.message.answer(MESSAGES['error_occurred'])

    await state.set_state(ForecastState.view_forecast) 