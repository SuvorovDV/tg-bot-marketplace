from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.bot.handlers import build_root_router
from app.config import settings
from app.db import get_session, init_db
from app.scheduler.main import run_daily_job
from app.services.sections import ensure_default_sections

log = logging.getLogger(__name__)


async def run_bot() -> None:
    await init_db()
    async with get_session() as s:
        await ensure_default_sections(s)

    if settings.telegram_api_server:
        api = TelegramAPIServer.from_base(settings.telegram_api_server.rstrip("/"))
        session = AiohttpSession(api=api)
        log.info("Using custom Telegram API server: %s", settings.telegram_api_server)
        bot = Bot(token=settings.bot_token, session=session)
    else:
        bot = Bot(token=settings.bot_token)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(build_root_router())
    await bot.set_my_commands(
        [
            BotCommand(command="start", description="Главное меню"),
            BotCommand(command="help", description="Справка и команды"),
            BotCommand(command="balance", description="Мой баланс"),
            BotCommand(command="my_products", description="Мои товары"),
            BotCommand(command="add_product", description="Добавить товар"),
            BotCommand(command="become_advertiser", description="Стать рекламодателем"),
            BotCommand(command="cancel", description="Отменить текущее действие"),
        ]
    )
    # Run APScheduler in the same process to keep deployment to one app on Fly.
    scheduler = AsyncIOScheduler()
    scheduler.add_job(run_daily_job, CronTrigger(hour=3, minute=0))
    scheduler.start()
    log.info("scheduler started; daily billing at 03:00 UTC")

    log.info("Bot starting polling")
    await dp.start_polling(bot)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_bot())


if __name__ == "__main__":
    main()
