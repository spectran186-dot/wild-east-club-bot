from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from keyboards.user import main_menu
from database import Database
from handlers.booking import booking_keyboard

db = Database()

router = Router()

@router.message(CommandStart())
async def start(message: Message):

    await message.answer(
        "🌊 <b>Добро пожаловать в Wild East Club!</b>\n\n"
        "Стирая границы, создавая моменты.\n\n"
        "Выберите нужный раздел 👇",
        reply_markup=main_menu,
    )


from aiogram import Router
from aiogram import F
from aiogram.types import Message

router = Router()

@router.message(F.text == "💰 Цены")
async def prices(message: Message):

    await message.answer(
        "💰 Стоимость\n\n"
        "🌊 р. Кия\n"
        "• Взрослый — 2500 ₽\n"
        "• Взрослый + ребёнок — +500 ₽\n"
        "• Со своим SUP — 500 ₽\n\n"
        "🌅 Амур (закат)\n"
        "• Взрослый — 1500 ₽\n"
        "• Взрослый + ребёнок — +500 ₽"
    )

@router.message(F.text == "📞 Контакты")
async def contacts(message: Message):

    await message.answer(
        "📞 Контакты\n\n"
        "Телефон:\n"
        "+79244160083\n\n"
        "Telegram:\n"
        "@wild_east_club\n\n"
        "Instagram:\n"
        "wild_east_club\n\n"
    )

@router.message(F.text == "❓ FAQ")
async def faq(message: Message):

    await message.answer(
        "❓ Частые вопросы\n\n"
        "• Нужен ли опыт? — Нет.\n"
        "• Выдают ли жилет? — Да.\n"
        "• Можно с ребёнком? — Да."
    )

@router.message(F.text == "📅 Мероприятия")
async def events(message: Message):

    events = db.get_events()

    if not events:
        await message.answer(
            "Пока мероприятий нет."
        )
        return

    for event in events:

        await message.answer(
            f"🌊 САП-сплав\n\n"
            f"📅 {event[2]}\n"
            f"🕒 {event[3]}\n"
            f"💰 {event[4]} ₽",
            reply_markup=booking_keyboard(event[0])
        )