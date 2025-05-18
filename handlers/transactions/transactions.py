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
    print(f"[DEBUG] Processing category selection. Callback data: {callback.data}")
    # Получаем индекс категории из callback_data
    category_data = callback.data.split('_')
    if len(category_data) != 3 or category_data[0] != "trans" or category_data[1] != "cat":
        await callback.message.edit_text("Ошибка при выборе категории")
        await state.clear()
        return
        
    try:
        category_index = int(category_data[2])
        # Получаем список категорий пользователя
        categories = await get_categories(callback.from_user.id)
        print(f"[DEBUG] User categories: {categories}")
        print(f"[DEBUG] Selected category index: {category_index}")
        
        if not categories or category_index >= len(categories):
            await callback.message.edit_text("Ошибка: категория не найдена")
            await state.clear()
            return
            
        category = categories[category_index]
        print(f"[DEBUG] Selected category name: {category}")
    except (ValueError, IndexError) as e:
        print(f"[DEBUG] Error processing category selection: {e}")
        await callback.message.edit_text("Ошибка при выборе категории")
        await state.clear()
        return

    await state.update_data(category=category)
    data = await state.get_data()
    print(f"[DEBUG] State data after category selection: {data}")
    
    # Проверка лимитов
    if data['type_'] == 1:  # Только для расходов
        limit_check = await check_limit_violation(
            callback.from_user.id,
            category,
            data['amount']
        )
        print(f"[DEBUG] Limit check result: {limit_check}")
        
        if limit_check:
            if limit_check["status"] == "violated":
                # Если есть нарушение лимита, показываем предупреждение
                text = MESSAGES['limit_warning'].format(
                    category=category,
                    limit_sum=round(limit_check['limit_sum'], 2),
                    current_spent=round(limit_check['current_spent'], 2),
                    new_amount=round(data['amount'], 2),
                    total_amount=round(limit_check['total_amount'], 2),
                    over_limit=round(limit_check['over_limit'], 2)
                )
                keyboard = await get_confirm_kb()
                await callback.message.edit_text(text, reply_markup=keyboard)
                await state.set_state(TransactionState.confirm_limit_override)
                return
            elif limit_check["status"] == "approaching":
                # Если приближаемся к лимиту, показываем информационное сообщение
                text = MESSAGES['limit_approaching'].format(
                    category=category,
                    limit_sum=round(limit_check['limit_sum'], 2),
                    current_spent=round(limit_check['current_spent'], 2),
                    new_amount=round(data['amount'], 2),
                    remaining=round(limit_check['remaining'], 2),
                    usage_percent=round(limit_check['usage_percent'], 1)
                )
                # Отправляем информационное сообщение
                await callback.message.answer(text)
                # Продолжаем с обычным подтверждением транзакции
                text = MESSAGES['confirm_transaction'].format(
                    amount=round(data['amount'], 2),
                    category=f"\nКатегория: {category}"
                )
                keyboard = await get_confirm_kb()
                await callback.message.edit_text(text, reply_markup=keyboard)
                await state.set_state(TransactionState.confirm_transaction)
                return

    # Если нет нарушения лимита, показываем обычное подтверждение
    text = MESSAGES['confirm_transaction'].format(
        amount=round(data['amount'], 2),
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
        category = data.get('category')

        # Добавляем транзакцию и проверяем лимиты
        transaction_id = await add_transaction(
            tg_id=tg_id, 
            type_=type_, 
            sum_=amount, 
            category=category,
            bot=callback.bot  # Передаем экземпляр бота
        )
        
        if transaction_id:
            # Проверяем лимит еще раз после добавления транзакции
            if type_ == 1 and category:  # Только для расходов
                limit_check = await check_limit_violation(tg_id, category, amount)
                
                if limit_check and limit_check["status"] == "violated":
                    await callback.message.edit_text(
                        '✅ Транзакция добавлена!\n\n'
                        '⚠️ Внимание! Превышен лимит по категории:\n'
                        f'Категория: {category}\n'
                        f'Превышение: {limit_check["over_limit"]:,.2f}₽'
                    )
                    return
                
            await callback.message.edit_text('✅ Транзакция успешно добавлена!')
        else:
            await callback.message.edit_text('❌ Ошибка при добавлении транзакции.')
    else:
        await callback.message.edit_text('❌ Добавление транзакции отменено.')

    await state.clear()