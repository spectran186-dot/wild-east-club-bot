from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from keyboards.user import main_menu
from database import Database

router = Router()

db = Database()

@router.message(CommandStart())
async def start(message: Message):

    db.add_user(
        telegram_id=message.from_user.id,
        first_name=message.from_user.first_name,
        username=message.from_user.username,
    )

    await message.answer(
        "🌊 Добро пожаловать в Wild East Club!\n\n"
        "Стирая границы, создавая моменты.\n\n"
        "Выберите нужный раздел 👇",
        reply_markup=main_menu,
    )