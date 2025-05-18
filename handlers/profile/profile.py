"""обработчик профиля пользователя: просмотр статистики, управление настройками и данными"""

import yaml
import os

from aiogram import Router, types, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters.command import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from keyboards.for_profile import get_profile_kb, get_settings_kb, get_confirm_reset_kb, get_back_kb
from keyboards.for_start import get_menu_kb, get_start_kb  # Импортируем клавиатуру меню и для регистрации
from database.db_methods import get_user, update_user, delete_user, is_registered, get_transactions_by_period
from datetime import datetime, timedelta

router = Router()

# Путь к messages.yaml в той же папке
MESSAGES_PATH = os.path.join(os.path.dirname(__file__), "messages.yaml")

# Загрузка сообщений
with open(MESSAGES_PATH, "r", encoding="utf-8") as file:
    MESSAGES = yaml.safe_load(file)


# Определение состояний FSM
class ProfileState(StatesGroup):
    waiting_for_name = State()


async def show_profile(message: Message, tg_id: int, state: FSMContext, edit_message: bool = False):
    """Обработчик команды /profile."""
    if not await is_registered(tg_id):
        await message.answer(MESSAGES["not_registered"])
        return

    user = await get_user(tg_id)
    name = user["name"] if user["name"] else "Не указано"
    total_sum = user["total_sum"] if user["total_sum"] is not None else 0.0
    categories = ", ".join(user["categories"]) if user["categories"] else "Нет категорий"

    # Получаем последние транзакции за последние 30 дней
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    transactions = await get_transactions_by_period(
        tg_id,
        start_date.strftime("%Y-%m-%d"),
        (end_date + timedelta(days=1)).strftime("%Y-%m-%d")
    )

    # Форматируем последние 5 транзакций
    transactions_text = ""
    if transactions:
        # Транзакции уже отсортированы по дате в запросе к БД, берем первые 5
        latest_transactions = transactions[:5]
        for t in latest_transactions:
            try:
                date = datetime.fromisoformat(t['date_time']).strftime("%d.%m")
                type_text = "➕ Доход" if t['type'] == 0 else "➖ Расход"
                category_text = f" ({t['category']})" if t['type'] == 1 and t['category'] else ""
                transactions_text += f"\n{date} | {type_text}: {t['sum']} руб.{category_text}"
            except (ValueError, KeyError) as e:
                continue
    else:
        transactions_text = "\nТранзакции не найдены"

    profile_text = MESSAGES["profile"].format(
        name=name,
        balance=total_sum,
        categories=categories,
        transactions=transactions_text
    )

    if edit_message:
        # Если это редактирование существующего сообщения
        await message.edit_text(profile_text, reply_markup=await get_profile_kb())
    else:
        # Если это новое сообщение
        # Сохраняем сообщение с emoji
        emoji_message = await message.answer(
            MESSAGES['profile_emoji'],
            reply_markup=types.ReplyKeyboardRemove(),
            disable_notification=True
        )
        await message.answer(profile_text, reply_markup=await get_profile_kb())


@router.message(Command("profile"))
@router.message(F.text == "Профиль")
async def show_profile_handler(message: Message, state: FSMContext):
    """Обработчик команды /profile и текста 'Профиль'."""
    tg_id = message.from_user.id
    await show_profile(message, tg_id, state)


@router.callback_query(F.data == "settings")
async def show_settings(callback: CallbackQuery, state: FSMContext):
    """Показать настройки профиля."""
    tg_id = callback.from_user.id
    if not await is_registered(tg_id):
        await callback.message.edit_text(MESSAGES["not_registered"], reply_markup=None)
        return

    await callback.message.edit_text(
        MESSAGES["settings"],
        reply_markup=await get_settings_kb()
    )
    await callback.answer()


@router.callback_query(F.data == "change_name")
async def start_change_name(callback: CallbackQuery, state: FSMContext):
    """Запрос нового имени."""
    tg_id = callback.from_user.id
    if not await is_registered(tg_id):
        await callback.message.edit_text(MESSAGES["not_registered"], reply_markup=None)
        return

    # Сохраняем message_id для последующего редактирования
    await state.update_data(settings_message_id=callback.message.message_id)

    await callback.message.edit_text(
        MESSAGES["request_new_name"],
        reply_markup=await get_back_kb("settings")
    )
    await state.set_state(ProfileState.waiting_for_name)
    await callback.answer()


@router.message(ProfileState.waiting_for_name)
async def process_new_name(message: Message, state: FSMContext):
    """Обработка нового имени."""
    tg_id = message.from_user.id
    if not await is_registered(tg_id):
        await message.answer(MESSAGES["not_registered"])
        return

    try:
        # Получаем сохраненный message_id
        data = await state.get_data()
        settings_message_id = data.get('settings_message_id')
        new_name = message.text.strip()


        await update_user(tg_id, name=new_name)

        # Редактируем предыдущее сообщение
        if settings_message_id:
            await message.bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=settings_message_id,
                text=MESSAGES["name_updated"].format(new_name=new_name),
                reply_markup=await get_settings_kb()
            )

        # Удаляем сообщение пользователя с новым именем
        await message.delete()

    except Exception as e:
        print(f"Error in process_new_name: {e}")
        if settings_message_id:
            await message.bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=settings_message_id,
                text=MESSAGES["error_occurred"],
                reply_markup=await get_settings_kb()
            )

    # Очищаем состояние
    await state.clear()


@router.callback_query(F.data == "reset_data")
async def confirm_reset_data(callback: CallbackQuery, state: FSMContext):
    """Подтверждение сброса данных."""
    tg_id = callback.from_user.id
    if not await is_registered(tg_id):
        await callback.message.edit_text(MESSAGES["not_registered"], reply_markup=None)
        return

    await callback.message.edit_text(
        MESSAGES["confirm_reset"],
        reply_markup=await get_confirm_reset_kb()
    )
    await callback.answer()


@router.callback_query(F.data == "confirm_reset")
async def reset_data(callback: CallbackQuery, state: FSMContext):
    """Сброс данных пользователя."""
    tg_id = callback.from_user.id
    # Удаляем все данные пользователя
    await delete_user(tg_id)
    # Отправляем сообщение и клавиатуру для регистрации
    await callback.message.edit_text(MESSAGES["data_reset"])
    await callback.message.answer(
        MESSAGES["not_registered"],
        reply_markup=await get_start_kb()
    )
    await callback.answer()
    # Очищаем состояние
    await state.clear()


@router.callback_query(F.data == "about_bot")
async def show_about_bot(callback: CallbackQuery, state: FSMContext):
    """Показать справку о боте."""
    tg_id = callback.from_user.id
    if not await is_registered(tg_id):
        await callback.message.edit_text(MESSAGES["not_registered"], reply_markup=None)
        return

    await callback.message.edit_text(
        MESSAGES["about_bot"],
        reply_markup=await get_back_kb("settings")
    )
    await callback.answer()


@router.callback_query(F.data.startswith("back_"))
async def handle_back(callback: CallbackQuery, state: FSMContext):
    """Обработка кнопки 'Назад'."""
    tg_id = callback.from_user.id
    # Разделяем callback_data на части: back_{action}
    parts = callback.data.split("_")
    action = parts[1]

    if action in ["profile", "settings"]:
        if not await is_registered(tg_id):
            await callback.message.edit_text(MESSAGES["not_registered"], reply_markup=None)
            return

    if action == "profile":
        await show_profile(callback.message, tg_id, state, edit_message=True)
    elif action == "settings":
        await show_settings(callback, state)
    elif action == "main":
        # Сначала редактируем текущее сообщение без клавиатуры
        await callback.message.edit_text(MESSAGES["to_menu"], reply_markup=None)
        # Отправляем новое сообщение с клавиатурой меню
        await callback.message.answer(MESSAGES["to_menu"], reply_markup=await get_menu_kb())
        # Очищаем состояние
        await state.clear()

    await callback.answer()
