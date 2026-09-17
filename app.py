import asyncio

from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand

import config
import database
from handlers import admin
from handlers.start import router as start_router

from handlers.menu import router as menu_router
from handlers.booking import router as booking_router

async def main():

    db = database.Database()

    db.create_tables()

    db.create_demo_routes()

    db.create_demo_events()

    bot = Bot(config.config.bot_token)

    dp = Dispatcher()

    dp.include_router(start_router)
    dp.include_router(menu_router)
    dp.include_router(booking_router)
    dp.include_router(admin.router)

    print("Wild East Club Bot started")
    
    await bot.set_my_commands([
        BotCommand(command="start", description="Главное меню"),
        BotCommand(command="admin", description="Админ-панель"),
    ])
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())