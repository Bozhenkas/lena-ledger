import yaml
import os

from aiogram import Router, types, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters.command import Command

from keyboards.for_profile import get_profile_kb, get_settings_kb, get_confirm_reset_kb, get_back_kb
from keyboards.for_start import get_menu_kb  # Импортируем клавиатуру меню
from database.db_methods import get_user, update_user, delete_user, is_registered

router = Router()

# Путь к messages.yaml в той же папке
MESSAGES_PATH = os.path.join(os.path.dirname(__file__), "messages.yaml")

# Загрузка сообщений
with open(MESSAGES_PATH, "r", encoding="utf-8") as file:
    MESSAGES = yaml.safe_load(file)

async def show_profile(message: Message, tg_id: int):
    """Обработчик команды /profile."""
    if not await is_registered(tg_id):
        await message.answer(MESSAGES["not_registered"])
        return

    user = await get_user(tg_id)
    name = user["name"] if user["name"] else "Не указано"
    total_sum = user["total_sum"] if user["total_sum"] is not None else 0.0
    categories = ", ".join(user["categories"]) if user["categories"] else "Нет категорий"
    transactions = "Транзакции пока не добавлены."  # Заглушка для 3 последних транзакций

    profile_text = MESSAGES["profile"].format(
        name=name,
        balance=total_sum,
        categories=categories,
        transactions=transactions
    )
    # Сохраняем сообщение с emoji
    emoji_message = await message.answer(MESSAGES['profile_emoji'], reply_markup=types.ReplyKeyboardRemove())
    message_id = emoji_message.message_id
    await message.answer(profile_text, reply_markup=await get_profile_kb(message_id))

@router.message(Command("profile"))
@router.message(F.text == "Профиль")
async def show_profile_handler(message: Message):
    """Обработчик команды /profile и текста 'Профиль'."""
    tg_id = message.from_user.id
    await show_profile(message, tg_id)

@router.callback_query(F.data == "settings")
async def show_settings(callback: CallbackQuery):
    """Показать настройки профиля."""
    tg_id = callback.from_user.id
    if not await is_registered(tg_id):
        await callback.message.edit_text(MESSAGES["not_registered"], reply_markup=None)
        return

    await callback.message.edit_text(
        MESSAGES["settings"],
        reply_markup=await get_settings_kb()
    )

@router.callback_query(F.data == "change_name")
async def start_change_name(callback: CallbackQuery):
    """Запрос нового имени."""
    tg_id = callback.from_user.id
    if not await is_registered(tg_id):
        await callback.message.edit_text(MESSAGES["not_registered"], reply_markup=None)
        return

    await callback.message.edit_text(
        MESSAGES["request_new_name"],
        reply_markup=await get_back_kb(action="settings")
    )

@router.message(F.text, F.reply_to_message)
async def process_new_name(message: Message):
    """Обработка нового имени."""
    tg_id = message.from_user.id
    if not await is_registered(tg_id):
        await message.answer(MESSAGES["not_registered"])
        return

    new_name = message.text.strip()
    await update_user(tg_id, name=new_name)
    await message.answer(MESSAGES["name_updated"].format(new_name=new_name))
    # Возвращаемся в профиль
    await show_profile(message, tg_id)

@router.callback_query(F.data == "reset_data")
async def confirm_reset_data(callback: CallbackQuery):
    """Подтверждение сброса данных."""
    tg_id = callback.from_user.id
    if not await is_registered(tg_id):
        await callback.message.edit_text(MESSAGES["not_registered"], reply_markup=None)
        return

    await callback.message.edit_text(
        MESSAGES["confirm_reset"],
        reply_markup=await get_confirm_reset_kb()
    )

@router.callback_query(F.data == "confirm_reset")
async def reset_data(callback: CallbackQuery):
    """Сброс данных пользователя."""
    tg_id = callback.from_user.id
    await delete_user(tg_id)
    await callback.message.edit_text(
        MESSAGES["data_reset"],
        reply_markup=await get_back_kb(action="main")
    )

@router.callback_query(F.data == "about_bot")
async def show_about_bot(callback: CallbackQuery):
    """Показать справку о боте."""
    tg_id = callback.from_user.id
    if not await is_registered(tg_id):
        await callback.message.edit_text(MESSAGES["not_registered"], reply_markup=None)
        return

    await callback.message.edit_text(
        MESSAGES["about_bot"],
        reply_markup=await get_back_kb(action="settings")
    )

@router.callback_query(F.data.startswith("back_"))
async def handle_back(callback: CallbackQuery):
    """Обработка кнопки 'Назад'."""
    tg_id = callback.from_user.id
    # Разделяем callback_data на части: back_{action}_{message_id}
    parts = callback.data.split("_")
    action = parts[1]

    # Извлекаем message_id, если он есть
    message_id = int(parts[2]) if len(parts) > 2 else None

    if action in ["profile", "settings"]:
        if not await is_registered(tg_id):
            await callback.message.edit_text(MESSAGES["not_registered"], reply_markup=None)
            return

    if action == "profile":
        await show_profile(callback.message, tg_id)
    elif action == "settings":
        await show_settings(callback)
    elif action == "main":
        # Редактируем текущее сообщение профиля
        await callback.message.edit_text(MESSAGES["back_to_main"], reply_markup=None)
        # Удаляем старое сообщение с emoji
        if message_id:
            await callback.message.bot.delete_message(
                chat_id=callback.message.chat.id,
                message_id=message_id
            )
            # Отправляем новое сообщение с той же emoji и клавиатурой меню
            await callback.message.bot.send_message(
                chat_id=callback.message.chat.id,
                text=MESSAGES['to_menu'],
                reply_markup=await get_menu_kb()
            )