'''
обработчик команды /start
'''

import yaml
import os

from aiogram import Router, types, F
from aiogram.filters.command import Command

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
async def cmd_start(message: types.Message):
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
        await message.answer(MESSAGES['reg'].format(name=tg_username or 'друг'),
                             reply_markup=await get_start_kb())
    else:
        await message.answer(MESSAGES['menu'], reply_markup=await get_menu_kb())


@router.message(F.text== 'Назад ↩️')
async def msg_menu(message: types.Message):
    await message.answer(MESSAGES['menu'], reply_markup=await get_menu_kb())