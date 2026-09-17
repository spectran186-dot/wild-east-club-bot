import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand

import config
import database
from handlers import admin
from handlers.admin_event import router as admin_event_router
from handlers.start import router as start_router
from handlers.menu import router as menu_router
from handlers.booking import router as booking_router


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger(__name__)


async def on_error(event):
    logger.exception("Unhandled bot error: %s", event.exception)


async def main():
    if not config.config.bot_token:
        raise RuntimeError("BOT_TOKEN is not configured")

    if not config.config.owner_id:
        raise RuntimeError("OWNER_ID is not configured")

    db = database.Database()
    await db.create_tables()
    await db.create_demo_routes()
    await db.create_demo_events()

    bot = Bot(config.config.bot_token)
    await bot.delete_webhook(drop_pending_updates=True)

    dp = Dispatcher()
    dp.errors.register(on_error)

    dp.include_router(start_router)
    dp.include_router(menu_router)
    dp.include_router(booking_router)
    # Этот роутер должен идти раньше общего admin.router,
    # чтобы callback add_event обрабатывался пошаговой формой.
    dp.include_router(admin_event_router)
    dp.include_router(admin.router)

    logger.info("Wild East Club Bot started")

    await bot.set_my_commands([
        BotCommand(command="start", description="Главное меню"),
        BotCommand(command="admin", description="Админ-панель"),
    ])

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
