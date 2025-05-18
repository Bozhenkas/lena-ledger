"""планировщик ежедневных проверок лимитов расходов и отправки уведомлений пользователям"""

from datetime import datetime
import asyncio
import pytz
from aiogram import Bot
from database.db_methods import get_expiring_limits, get_violated_limits

async def check_limits(bot: Bot):
    """performs daily limit checks and sends notifications for expiring and violated limits."""
    while True:
        # Ждем до 8:00 по МСК
        moscow_tz = pytz.timezone('Europe/Moscow')
        now = datetime.now(moscow_tz)
        target_time = now.replace(hour=8, minute=0, second=0, microsecond=0)
        
        if now >= target_time:
            target_time = target_time.replace(day=target_time.day + 1)
        
        wait_seconds = (target_time - now).total_seconds()
        await asyncio.sleep(wait_seconds)
        
        # Проверка истекающих лимитов
        expiring_limits = await get_expiring_limits()
        for limit in expiring_limits:
            await bot.send_message(
                limit["tg_id"],
                f"⚠️ Напоминание: завтра истекает лимит!\n\n"
                f"Категория: {limit['category']}\n"
                f"Лимит: {limit['limit_sum']}₽"
            )
        
        # Проверка нарушенных лимитов
        violated_limits = await get_violated_limits()
        for limit in violated_limits:
            await bot.send_message(
                limit["tg_id"],
                f"🚫 Внимание! Превышен лимит расходов!\n\n"
                f"Категория: {limit['category']}\n"
                f"Установленный лимит: {limit['limit_sum']}₽\n"
                f"Текущие расходы: {limit['current_spent']}₽\n"
                f"Превышение: {limit['current_spent'] - limit['limit_sum']}₽"
            )
        
        # Ждем 24 часа перед следующей проверкой
        await asyncio.sleep(24 * 60 * 60) 