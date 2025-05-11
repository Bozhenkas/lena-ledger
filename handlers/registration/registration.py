import yaml
import os

from aiogram import Router, types, F
from aiogram.filters.command import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from keyboards.for_start import get_start_kb
from keyboards.for_registration import *  # импортируем клавиатуры
from database.db_methods import get_user, add_user, update_user
from handlers.categories.categories import AddCategory

# создание роутера
router = Router()

# путь к messages.yaml в той же папке
MESSAGES_PATH = os.path.join(os.path.dirname(__file__), 'messages.yaml')

# загрузка сообщений
with open(MESSAGES_PATH, 'r', encoding='utf-8') as file:
    MESSAGES = yaml.safe_load(file)


# состояния для регистрации
class Registration(StatesGroup):
    name_input = State()
    sum_input = State()
    confirm_registration = State()


@router.message(Command('registration'))
@router.message(F.text == 'Начать регистрацию')
async def cmd_register(message: types.Message, state: FSMContext):
    tg_id = message.from_user.id
    tg_username = message.from_user.username

    user = await get_user(tg_id)
    if user and user['name'] and user['total_sum'] is not None:
        await message.answer(
            MESSAGES['already_registered'].format(name=user['name'])
        )
        return

    if not user:
        await add_user(tg_id, tg_username)

    await message.answer(
        MESSAGES['request_name']
    )
    await state.set_state(Registration.name_input)


@router.message(Command('cancel'))
async def cancel_registration(message: types.Message, state: FSMContext):
    await message.answer(
        MESSAGES['registration_cancelled'],
        reply_markup=await get_start_kb()
    )
    await state.clear()


@router.message(Registration.name_input, F.text)
async def process_name(message: types.Message, state: FSMContext):
    name = message.text.strip()
    await state.update_data(name=name)

    await message.answer(
        MESSAGES['request_sum']
    )
    await state.set_state(Registration.sum_input)


@router.message(Registration.sum_input, F.text)
async def process_initial_sum(message: types.Message, state: FSMContext):
    try:
        initial_sum = float(message.text.strip())
        if initial_sum < 0:
            raise ValueError
    except ValueError:
        await message.answer(
            MESSAGES['request_sum_error']
        )
        return

    user_data = await state.get_data()
    await state.update_data(sum=initial_sum, name=user_data['name'])

    await message.answer(
        MESSAGES['confirm_registration'].format(name=user_data['name'], sum=initial_sum),
        reply_markup=await get_confirm_kb()
    )
    await state.set_state(Registration.confirm_registration)


@router.message(Registration.confirm_registration, F.text)
async def process_confirm_registration(message: types.Message, state: FSMContext):
    if message.text == 'Да':
        user_data = await state.get_data()
        name = user_data['name']
        initial_sum = user_data['sum']
        await update_user(message.from_user.id, name=name, total_sum=initial_sum)

        await message.answer(
            MESSAGES['success'].format(name=name, sum=initial_sum))
        await message.answer(
            MESSAGES['pls_add_categories'],
            reply_markup=await get_add_category_kb()
        )
        await state.clear()
    else:
        await message.answer(
            MESSAGES['request_name']
        )
        await state.set_state(Registration.name_input)
