"""обработчик финансовых транзакций: добавление доходов и расходов по категориям"""

import yaml
import os

from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from keyboards.for_transactions import get_categories_kb, get_confirm_kb
from database.db_methods import (
    get_categories,
    add_transaction,
    check_limit_violation
)

# Создание роутера
router = Router()

# Путь к messages.yaml в той же папке
MESSAGES_PATH = os.path.join(os.path.dirname(__file__), 'messages.yaml')

# Загрузка сообщений
with open(MESSAGES_PATH, 'r', encoding='utf-8') as file:
    MESSAGES = yaml.safe_load(file)

# Определение состояний
class TransactionState(StatesGroup):
    enter_amount = State()         # Ввод суммы
    select_category = State()      # Выбор категории
    confirm_transaction = State()  # Подтверждение транзакции
    confirm_limit_override = State()  # Подтверждение превышения лимита

# Обработчик команды "Потратил"
@router.message(F.text == 'Потратил')
async def cmd_spent(message: types.Message, state: FSMContext):
    await message.answer(MESSAGES['enter_amount'])
    await state.set_state(TransactionState.enter_amount)
    await state.update_data(type_=1)  # 1 - расход

# Обработчик команды "Получил"
@router.message(F.text == 'Получил')
async def cmd_received(message: types.Message, state: FSMContext):
    await message.answer(MESSAGES['enter_amount'])
    await state.set_state(TransactionState.enter_amount)
    await state.update_data(type_=0)  # 0 - доход

# Обработка ввода суммы
@router.message(TransactionState.enter_amount)
async def process_amount(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text)
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.answer('Пожалуйста, введите положительное число.')
        return

    await state.update_data(amount=amount)

    tg_id = message.from_user.id
    categories = await get_categories(tg_id)
    if not categories and (await state.get_data())['type_'] == 1:  # Проверка категорий только для расходов
        await message.answer(MESSAGES['no_categories'])
        await state.clear()
        return

    if (await state.get_data())['type_'] == 1:  # Для расходов показываем категории
        keyboard = await get_categories_kb(categories)
        await message.answer(MESSAGES['select_category'], reply_markup=keyboard)
        await state.set_state(TransactionState.select_category)
    else:  # Для доходов сразу переходим к подтверждению
        data = await state.get_data()
        text = MESSAGES['confirm_transaction'].format(amount=amount, category='')
        keyboard = await get_confirm_kb()
        await message.answer(text, reply_markup=keyboard)
        await state.set_state(TransactionState.confirm_transaction)

# Обработка выбора категории (только для расходов)
@router.callback_query(TransactionState.select_category)
async def process_category(callback: types.CallbackQuery, state: FSMContext):
    category = callback.data
    await state.update_data(category=category)
    data = await state.get_data()
    
    # Проверка лимитов
    if data['type_'] == 1:  # Только для расходов
        limit_violation = await check_limit_violation(
            callback.from_user.id,
            category,
            data['amount']
        )
        
        if limit_violation:
            # Если есть нарушение лимита, показываем предупреждение
            total_amount = limit_violation['current_spent'] + data['amount']
            over_limit = total_amount - limit_violation['limit_sum']
            
            text = MESSAGES['limit_warning'].format(
                category=category,
                limit_sum=limit_violation['limit_sum'],
                current_spent=limit_violation['current_spent'],
                new_amount=data['amount'],
                total_amount=total_amount,
                over_limit=over_limit
            )
            keyboard = await get_confirm_kb()
            await callback.message.edit_text(text, reply_markup=keyboard)
            await state.set_state(TransactionState.confirm_limit_override)
            return

    # Если нет нарушения лимита, показываем обычное подтверждение
    text = MESSAGES['confirm_transaction'].format(
        amount=data['amount'],
        category=f"\nКатегория: {category}" if data['type_'] == 1 else ''
    )
    keyboard = await get_confirm_kb()
    await callback.message.edit_text(text, reply_markup=keyboard)
    await state.set_state(TransactionState.confirm_transaction)

# Обработка подтверждения транзакции
@router.callback_query(TransactionState.confirm_transaction)
@router.callback_query(TransactionState.confirm_limit_override)
async def process_confirm(callback: types.CallbackQuery, state: FSMContext):
    if callback.data == 'confirm':
        data = await state.get_data()
        tg_id = callback.from_user.id
        type_ = data['type_']
        amount = data['amount']
        category = data.get('category') if type_ == 1 else None  # Категория только для расходов

        transaction_id = await add_transaction(tg_id, type_, amount, category)
        if transaction_id:
            await callback.message.edit_text('Транзакция успешно добавлена!')
        else:
            await callback.message.edit_text('Ошибка при добавлении транзакции.')
    else:
        await callback.message.edit_text('Добавление транзакции отменено.')

    await state.clear()