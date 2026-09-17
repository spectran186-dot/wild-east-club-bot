from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from keyboards.user import main_menu
from database import Database

router = Router()
db = Database()

# Сообщения бота, которые можно удалить при следующем /start.
# Храним только ID сообщений текущего процесса — старые сообщения,
# которые не были сохранены, Telegram API удалить не позволит.
_bot_messages = {}


async def remember_bot_message(user_id: int, message: Message):
    _bot_messages.setdefault(user_id, []).append(message.message_id)


async def clear_bot_messages(message: Message):
    user_id = message.from_user.id
    message_ids = _bot_messages.pop(user_id, [])

    for message_id in message_ids:
        try:
            await message.bot.delete_message(message.chat.id, message_id)
        except Exception:
            pass

    # Удаляем сам /start, чтобы после очистки чат начинался с меню.
    try:
        await message.delete()
    except Exception:
        pass


@router.message(CommandStart())
async def start(message: Message):
    await clear_bot_messages(message)

    await db.add_user(
        telegram_id=message.from_user.id,
        first_name=message.from_user.first_name,
        username=message.from_user.username,
    )

    sent_message = await message.answer(
        "🌊 Добро пожаловать в Wild East Club!\n\n"
        "Стирая границы, создавая моменты.\n\n"
        "Выберите нужный раздел 👇",
        reply_markup=main_menu,
    )
    await remember_bot_message(message.from_user.id, sent_message)
