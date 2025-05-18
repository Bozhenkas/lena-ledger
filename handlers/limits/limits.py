"""обработчик управления лимитами расходов: создание, просмотр, удаление и отслеживание"""

from datetime import datetime, timedelta
import yaml
from pathlib import Path
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database.db_methods import add_limit, get_user_limits, delete_limit, get_categories
from keyboards.for_limits import (
    get_period_keyboard,
    get_limit_actions_keyboard,
    get_confirm_delete_keyboard,
    get_limits_list_keyboard
)
from keyboards.for_categories import get_categories_kb
from keyboards.for_start import get_menu_kb

router = Router()

# Загрузка сообщений из YAML файла
with open(Path(__file__).parent / "message.yaml", "r", encoding="utf-8") as file:
    MESSAGES = yaml.safe_load(file)["limits"]


class LimitStates(StatesGroup):
    """Состояния для FSM при работе с лимитами"""
    CHOOSING_PERIOD = State()
    ENTERING_PERIOD_VALUE = State()
    ENTERING_AMOUNT = State()
    CHOOSING_CATEGORY = State()
    CONFIRMING_DELETE = State()


@router.message(Command("limits"))
@router.message(F.text == "Лимиты")
async def cmd_limits(message: Message, state: FSMContext):
    """Обработчик команды /limits и кнопки 'Лимиты'"""
    # Отправляем placeholder с удалением клавиатуры
    placeholder_msg = await message.answer(
        MESSAGES["placeholder"],
        reply_markup=ReplyKeyboardRemove(),
        disable_notification=True
    )
    # Сохраняем ID сообщения-заглушки в FSM
    await state.update_data(placeholder_msg_id=placeholder_msg.message_id)
    # Отправляем основное сообщение с инлайн-клавиатурой
    await message.answer(MESSAGES["welcome"], reply_markup=get_limit_actions_keyboard())


@router.callback_query(F.data == "limit_back_to_menu")
async def process_back_to_menu(callback: CallbackQuery, state: FSMContext):
    """Обработка возврата в главное меню"""
    # Очищаем состояние FSM
    await state.clear()
    # Отправляем сообщение с клавиатурой меню
    await callback.message.answer(MESSAGES["menu"], reply_markup=await get_menu_kb())
    await callback.answer()


@router.callback_query(F.data == "limit_add")
async def process_limit_add(callback: CallbackQuery, state: FSMContext):
    """Начало процесса добавления лимита"""
    await state.set_state(LimitStates.CHOOSING_PERIOD)
    keyboard = get_period_keyboard()
    await callback.message.edit_text(MESSAGES["enter_period"], reply_markup=keyboard)


@router.callback_query(F.data.startswith("period_"))
async def process_period_selection(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора периода"""
    period_type = callback.data.split("_")[1]
    await state.update_data(period_type=period_type)

    period_message_keys = {
        "days": "enter_days",
        "weeks": "enter_weeks",
        "months": "enter_months",
        "years": "enter_years"
    }

    await state.set_state(LimitStates.ENTERING_PERIOD_VALUE)
    await callback.message.edit_text(MESSAGES[period_message_keys[period_type]])


@router.message(LimitStates.ENTERING_PERIOD_VALUE)
async def process_period_value(message: Message, state: FSMContext):
    """Обработка введенного значения периода"""
    try:
        value = int(message.text)
        data = await state.get_data()
        period_type = data["period_type"]

        max_values = {
            "days": 365,
            "weeks": 52,
            "months": 12,
            "years": 5
        }

        if value < 1 or value > max_values[period_type]:
            await message.answer(MESSAGES["invalid_period"])
            return

        # Расчет дат
        start_date = datetime.now()
        if period_type == "days":
            end_date = start_date + timedelta(days=value)
        elif period_type == "weeks":
            end_date = start_date + timedelta(weeks=value)
        elif period_type == "months":
            end_date = start_date + timedelta(days=value * 30)
        else:  # years
            end_date = start_date + timedelta(days=value * 365)

        await state.update_data(
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d")
        )

        await state.set_state(LimitStates.ENTERING_AMOUNT)
        await message.answer(MESSAGES["enter_amount"])

    except ValueError:
        await message.answer(MESSAGES["invalid_period"])


@router.message(LimitStates.ENTERING_AMOUNT)
@router.message(LimitStates.ENTERING_AMOUNT)
async def process_amount(message: Message, state: FSMContext):
    """Обработка введенной суммы лимита"""
    try:
        amount = float(message.text)
        if amount <= 0:
            raise ValueError

        await state.update_data(amount=amount)
        await state.set_state(LimitStates.CHOOSING_CATEGORY)

        # Получаем категории пользователя и создаем клавиатуру
        categories = await get_categories(message.from_user.id)
        keyboard = await get_categories_kb(categories, page=0)

        await message.answer(MESSAGES["select_category"], reply_markup=keyboard)

    except ValueError:
        await message.answer(MESSAGES["invalid_amount"])


@router.callback_query(LimitStates.CHOOSING_CATEGORY)
async def process_category_selection(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора категории"""
    if callback.data.startswith("category_"):
        # Получаем индекс категории из callback_data
        try:
            category_index = int(callback.data.replace("category_", ""))
            # Получаем список категорий пользователя
            user_categories = await get_categories(callback.from_user.id)
            
            # Проверяем, что индекс находится в пределах списка
            if 0 <= category_index < len(user_categories):
                # Получаем реальное название категории по индексу
                category = user_categories[category_index]
                # Отладочный вывод
                print(f"Selected category index: {category_index}")
                print(f"Selected category name: {category}")
                print(f"User categories: {user_categories}")
                
                data = await state.get_data()
                
                if await add_limit(
                    callback.from_user.id,
                    data["start_date"],
                    data["end_date"],
                    category,
                    data["amount"]
                ):
                    await callback.message.edit_text(
                        MESSAGES["limit_added"].format(
                            category=category,
                            amount=data["amount"],
                            start_date=data["start_date"],
                            end_date=data["end_date"]
                        ),
                        reply_markup=get_limit_actions_keyboard()
                    )
                else:
                    await callback.message.edit_text(
                        "⚠️ Не удалось добавить лимит. Возможно, произошла ошибка при сохранении.",
                        reply_markup=get_limit_actions_keyboard()
                    )
            else:
                await callback.message.edit_text(
                    "⚠️ Ошибка: выбранная категория не найдена в списке ваших категорий.",
                    reply_markup=get_limit_actions_keyboard()
                )
        except ValueError:
            await callback.message.edit_text(
                "⚠️ Произошла ошибка при обработке выбора категории.",
                reply_markup=get_limit_actions_keyboard()
            )
        
        await state.clear()
    elif callback.data == "next_page" or callback.data == "prev_page":
        # Обработка пагинации категорий
        current_page = int(callback.message.reply_markup.inline_keyboard[-1][0].callback_data.split("_")[-1])
        new_page = current_page + 1 if callback.data == "next_page" else current_page - 1
        
        categories = await get_categories(callback.from_user.id)
        keyboard = await get_categories_kb(categories, page=new_page)
        
        await callback.message.edit_text(
            MESSAGES["select_category"],
            reply_markup=keyboard
        )


@router.callback_query(F.data == "limit_list")
async def process_limit_list(callback: CallbackQuery):
    """Отображение списка активных лимитов"""
    limits = await get_user_limits(callback.from_user.id)

    if not limits:
        await callback.message.edit_text(
            MESSAGES["no_limits"],
            reply_markup=get_limit_actions_keyboard()
        )
        return

    limits_text = ""
    for limit in limits:
        limits_text += (
            f"• {limit['category']}: {limit['limit_sum']}₽\n"
            f"  До {limit['end_date']}\n\n"
        )

    await callback.message.edit_text(
        MESSAGES["limits_list"].format(limits_text=limits_text),
        reply_markup=get_limit_actions_keyboard()
    )


@router.callback_query(F.data == "limit_delete")
async def process_limit_delete(callback: CallbackQuery):
    """Процесс удаления лимита"""
    limits = await get_user_limits(callback.from_user.id)

    if not limits:
        await callback.message.edit_text(
            MESSAGES["no_limits"],
            reply_markup=get_limit_actions_keyboard()
        )
        return

    await callback.message.edit_text(
        "Выберите лимит для удаления:",
        reply_markup=get_limits_list_keyboard(limits)
    )


@router.callback_query(F.data.startswith("delete_limit_"))
async def confirm_limit_delete(callback: CallbackQuery, state: FSMContext):
    """Подтверждение удаления лимита"""
    limit_id = int(callback.data.split("_")[2])
    await state.update_data(limit_id=limit_id)

    limits = await get_user_limits(callback.from_user.id)
    limit_info = next((l for l in limits if l["limit_id"] == limit_id), None)

    if not limit_info:
        await callback.message.edit_text(
            "⚠️ Лимит не найден.",
            reply_markup=get_limit_actions_keyboard()
        )
        return

    await state.set_state(LimitStates.CONFIRMING_DELETE)
    limit_info_text = (
        f"Категория: {limit_info['category']}\n"
        f"Сумма: {limit_info['limit_sum']}₽\n"
        f"До: {limit_info['end_date']}"
    )
    await callback.message.edit_text(
        MESSAGES["confirm_delete"].format(limit_info=limit_info_text),
        reply_markup=get_confirm_delete_keyboard(limit_id)
    )


@router.callback_query(F.data.startswith("confirm_delete_"))
async def process_delete_confirmation(callback: CallbackQuery, state: FSMContext):
    """Обработка подтверждения удаления"""
    limit_id = int(callback.data.split("_")[2])

    if await delete_limit(limit_id, callback.from_user.id):
        await callback.message.edit_text(
            MESSAGES["limit_deleted"],
            reply_markup=get_limit_actions_keyboard()
        )
    else:
        await callback.message.edit_text(
            "⚠️ Не удалось удалить лимит. Попробуйте позже.",
            reply_markup=get_limit_actions_keyboard()
        )

    await state.clear()


@router.callback_query(F.data == "cancel_delete")
async def process_delete_cancellation(callback: CallbackQuery, state: FSMContext):
    """Обработка отмены удаления"""
    await state.clear()
    await callback.message.edit_text(
        MESSAGES["operation_cancelled"],
        reply_markup=get_limit_actions_keyboard()
    )
