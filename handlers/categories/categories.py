import yaml
import os

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters.command import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from keyboards.for_start import get_menu_kb
from keyboards.for_categories import get_add_category_kb, get_categories_kb, get_add_more_kb
from database.db_methods import get_categories, add_category, update_user, is_registered

router = Router()

# Локальный словарь для хранения категорий (обновляется при вызове /categories)
categories_dict = {}

# путь к messages.yaml в той же папке
MESSAGES_PATH = os.path.join(os.path.dirname(__file__), "messages.yaml")

# загрузка сообщений
with open(MESSAGES_PATH, "r", encoding="utf-8") as file:
    MESSAGES = yaml.safe_load(file)


# Определение FSM для добавления категории
class AddCategory(StatesGroup):
    waiting_for_category_name = State()
    confirming_more_categories = State()


@router.message(F.text == "Категории")
@router.message(Command("categories"))
async def show_categories(message: Message, state: FSMContext):
    """Обработчик команды /categories и текста 'Категории'."""
    tg_id = message.from_user.id
    if not await is_registered(tg_id):
        await message.answer(MESSAGES["not_registered"])
        return

    # Получаем список категорий из базы
    categories = await get_categories(tg_id)

    # Обновляем локальный словарь категорий (key - callback_data, value - название)
    global categories_dict
    categories_dict = {f"category_{i}": cat for i, cat in enumerate(categories)}

    # Сохраняем текущий список категорий в FSM для сравнения при обновлении
    await state.update_data(current_categories=categories)

    # Первое сообщение с клавиатурой добавления
    await message.answer(MESSAGES["placeholder"], reply_markup=await get_add_category_kb(), disable_notification=True)

    # Второе сообщение с инлайн-кнопками категорий (пагинация до 5 за раз)
    categories_message = await message.answer(
        MESSAGES["show_categories"],
        reply_markup=await get_categories_kb(categories, page=0)
    )
    # Сохраняем message_id в FSM-контексте
    await state.update_data(categories_message_id=categories_message.message_id)


@router.message(F.text.in_(["Добавить категорию", "Добавить категории"]))
async def start_add_category(message: Message, state: FSMContext):
    """Начало процесса добавления категории."""
    await message.answer(MESSAGES["request_category"])
    await state.set_state(AddCategory.waiting_for_category_name)


@router.message(AddCategory.waiting_for_category_name)
async def process_category_name(message: Message, state: FSMContext):
    """Обработка введенного названия категории."""
    category_name = message.text.strip()
    tg_id = message.from_user.id

    # Получаем текущий список категорий из FSM-контекста для сравнения
    data = await state.get_data()
    old_categories = data.get("current_categories", [])

    try:
        await add_category(tg_id, category_name)
        # Обновляем локальный словарь
        categories = await get_categories(tg_id)
        global categories_dict
        categories_dict[f"category_{len(categories) - 1}"] = category_name

        # Получаем ID сообщения с категориями из FSM-контекста
        categories_message_id = data.get("categories_message_id")

        # Обновляем сообщение с категориями только если они изменились
        if categories_message_id and categories != old_categories:
            await message.bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=categories_message_id,
                text=MESSAGES["show_categories"],
                reply_markup=await get_categories_kb(categories, page=0)
            )

        # Обновляем список категорий в FSM-контексте
        await state.update_data(current_categories=categories)

        await message.answer(
            MESSAGES["category_added"].format(category_name=category_name),
            reply_markup=await get_add_more_kb()
        )
        await state.set_state(AddCategory.confirming_more_categories)
    except ValueError as e:
        # Если категория уже существует, список не изменился, поэтому не редактируем сообщение
        await message.answer(MESSAGES["category_exists"])
        await state.set_state(AddCategory.waiting_for_category_name)


@router.message(AddCategory.confirming_more_categories, F.text)
async def process_add_more_choice(message: Message, state: FSMContext):
    """Обработка выбора 'Добавить ещё' или 'Хватит'."""
    tg_id = message.from_user.id
    categories = await get_categories(tg_id)

    # Получаем ID сообщения с категориями из FSM-контекста
    data = await state.get_data()
    categories_message_id = data.get("categories_message_id")
    old_categories = data.get("current_categories", [])

    if message.text == "Добавить ещё":
        # Обновляем сообщение с категориями перед добавлением новой, только если они изменились
        if categories_message_id and categories != old_categories:
            await message.bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=categories_message_id,
                text=MESSAGES["show_categories"],
                reply_markup=await get_categories_kb(categories, page=0)
            )
        await message.answer(
            MESSAGES["request_category"],
            reply_markup=None
        )
        await state.set_state(AddCategory.waiting_for_category_name)
    else:  # "Хватит"
        # Обновляем сообщение с категориями перед выходом, только если они изменились
        if categories_message_id and categories != old_categories:
            await message.bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=categories_message_id,
                text=MESSAGES["show_categories"],
                reply_markup=await get_categories_kb(categories, page=0)
            )
        await message.answer(
            MESSAGES["category_add_completed"],
            reply_markup=await get_menu_kb()
        )
        await state.clear()


@router.callback_query(F.data.startswith("page_"))
async def handle_pagination(callback: CallbackQuery):
    """Обработка пагинации категорий."""
    page = int(callback.data.split("_")[1])
    categories = await get_categories(callback.from_user.id)

    await callback.message.edit_text(
        MESSAGES["show_categories"],
        reply_markup=await get_categories_kb(categories, page)
    )
    await callback.answer()


@router.message(F.text.in_(["Назад ↩️", "/start"]))
async def back_to_menu(message: Message, state: FSMContext):
    """Обработчик для выхода в меню через 'Назад ↩️' или '/start'."""
    await state.clear()
    await message.answer(
        MESSAGES["back_to_menu"],
        reply_markup=None
    )
