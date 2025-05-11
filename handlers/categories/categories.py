"""
обработчик для добавления категорий.
"""

import yaml
import os

from aiogram import Router, types, F
from aiogram.filters.command import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from keyboards.for_registration import get_category_continue_kb  # импортируем клавиатуру
from database.db_methods import get_user, update_user

# создание роутера
router = Router()

# путь к messages.yaml в той же папке
MESSAGES_PATH = os.path.join(os.path.dirname(__file__), "messages.yaml")

# загрузка сообщений
with open(MESSAGES_PATH, "r", encoding="utf-8") as file:
    MESSAGES = yaml.safe_load(file)

# состояния для добавления категорий
class AddCategory(StatesGroup):
    waiting_for_category_name = State()
    confirming_more_categories = State()

@router.message(Command("addcategory"))
async def cmd_add_category(message: types.Message, state: FSMContext):
    tg_id = message.from_user.id
    user = await get_user(tg_id)
    if not user:
        await message.answer(
            MESSAGES["not_registered"]["text"]
        )
        return

    await state.update_data(categories=[])
    await message.answer(
        MESSAGES["request_category"]["text"]
    )
    await state.set_state(AddCategory.waiting_for_category_name)

@router.message(AddCategory.waiting_for_category_name, F.text)
async def process_category_name(message: types.Message, state: FSMContext):
    category_name = message.text.strip()

    if category_name in ["Да", "Отмена"]:
        await message.answer(
            MESSAGES["invalid_input"]["text"]
        )
        return

    user_data = await state.get_data()
    categories = user_data.get("categories", [])
    user = await get_user(message.from_user.id)
    all_categories = user["categories"] + categories

    if category_name in all_categories:
        await message.answer(
            MESSAGES["category_exists"]["text"].format(category=category_name)
        )
        return

    categories.append(category_name)
    await state.update_data(categories=categories)

    await message.answer(
        MESSAGES["success_category"]["text"].format(category=category_name)
    )

    if len(categories) < 3:
        await message.answer(
            MESSAGES["ask_more_categories"]["text"],
            reply_markup=await get_category_continue_kb()
        )
        await state.set_state(AddCategory.confirming_more_categories)
    else:
        await message.answer(
            MESSAGES["max_categories"]["text"].format(count=len(categories))
        )
        all_categories = user["categories"] + categories
        await update_user(message.from_user.id, categories=all_categories)
        await state.clear()

@router.message(AddCategory.confirming_more_categories, F.text)
async def process_continue_choice(message: types.Message, state: FSMContext):
    if message.text == "Да":
        await message.answer(
            MESSAGES["request_category"]["text"],
            reply_markup=None
        )
        await state.set_state(AddCategory.waiting_for_category_name)
    else:  # "Отмена"
        user_data = await state.get_data()
        categories = user_data.get("categories", [])
        if categories:
            user = await get_user(message.from_user.id)
            all_categories = user["categories"] + categories
            await update_user(message.from_user.id, categories=all_categories)
            await message.answer(
                MESSAGES["success"]["text"].format(count=len(categories))
            )
        else:
            await message.answer(
                MESSAGES["no_categories"]["text"]
            )
        await state.clear()