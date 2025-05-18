"""обработчик команды /start, регистрация новых пользователей и навигация по главному меню"""

import yaml
import os

from aiogram import Router, types, F
from aiogram.filters.command import Command
from aiogram.fsm.context import FSMContext

from keyboards.for_start import get_start_kb, get_menu_kb
from database.db_methods import get_user, add_user, is_registered  # импорт из database/

# создание роутера
router = Router()

# путь к messages.yaml в той же папке
MESSAGES_PATH = os.path.join(os.path.dirname(__file__), 'messages.yaml')

# загрузка сообщений
with open(MESSAGES_PATH, 'r', encoding='utf-8') as file:
    MESSAGES = yaml.safe_load(file)


@router.message(Command('start'))
async def cmd_start(message: types.Message, state: FSMContext):
    # Очищаем состояние FSM при старте
    await state.clear()
    
    # получение tg_id и tg_username из сообщения
    tg_id = message.from_user.id
    tg_username = message.from_user.username

    # проверка пользователя в базе
    user = await get_user(tg_id)
    if not user:
        # добавление нового пользователя, если его нет
        await add_user(tg_id, tg_username)

    if not await is_registered(tg_id):
        # отправляем клавиатуру с регистрацией
        await message.answer(
            MESSAGES['reg'].format(name=tg_username or 'друг'),
            reply_markup=await get_start_kb()
        )
    else:
        await message.answer(MESSAGES['menu'], reply_markup=await get_menu_kb())


@router.message(Command('cancel'))
async def cmd_cancel(message: types.Message, state: FSMContext):
    """Обработчик команды /cancel - отмена текущего действия и возврат в меню"""
    # Очищаем состояние FSM
    await state.clear()
    
    # Получаем данные о пользователе
    tg_id = message.from_user.id
    if not await is_registered(tg_id):
        await message.answer(MESSAGES['not_registered'])
        return
        
    # Возвращаемся в меню
    await message.answer(MESSAGES['menu'], reply_markup=await get_menu_kb())


@router.message(F.text == 'Назад ↩️')
async def msg_menu(message: types.Message, state: FSMContext):
    # Очищаем состояние FSM
    await state.clear()
    await message.answer(MESSAGES['menu'], reply_markup=await get_menu_kb())