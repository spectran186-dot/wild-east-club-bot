from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from database import Database
from handlers.booking import booking_keyboard
from keyboards.user import main_menu, back_to_menu_keyboard


db = Database()
router = Router()


async def show_prices(target):
    await target.edit_text(
        "💰 <b>Стоимость</b>\n\n"
        "🌊 р. Кия\n"
        "• Взрослый — 2500 ₽\n"
        "• Взрослый + ребёнок — +500 ₽\n"
        "• Со своим SUP — 500 ₽\n\n"
        "🌅 Амур (закат)\n"
        "• Взрослый — 1500 ₽\n"
        "• Взрослый + ребёнок — +500 ₽",
        reply_markup=back_to_menu_keyboard(),
        parse_mode="HTML",
    )


async def show_contacts(target):
    await target.edit_text(
        "📞 <b>Контакты</b>\n\n"
        "Телефон:\n"
        "+79244160083\n\n"
        "Telegram:\n"
        "@wild_east_club\n\n"
        "Instagram:\n"
        "wild_east_club",
        reply_markup=back_to_menu_keyboard(),
        parse_mode="HTML",
    )


async def show_faq(target):
    await target.edit_text(
        "❓ <b>Частые вопросы</b>\n\n"
        "• Нужен ли опыт? — Нет.\n"
        "• Выдают ли жилет? — Да.\n"
        "• Можно с ребёнком? — Да.",
        reply_markup=back_to_menu_keyboard(),
        parse_mode="HTML",
    )


async def show_events(target):
    events_list = await db.get_events()

    if not events_list:
        await target.edit_text(
            "📅 <b>Мероприятия</b>\n\nПока мероприятий нет.",
            reply_markup=back_to_menu_keyboard(),
            parse_mode="HTML",
        )
        return

    lines = ["📅 <b>Мероприятия</b>", ""]
    keyboard = []

    for event in events_list:
        lines.extend([
            "🌊 <b>САП-сплав</b>",
            f"📅 {event[2]}",
            f"🕒 {event[3]}",
            f"💰 {event[4]} ₽",
            "",
        ])
        keyboard.append(booking_keyboard(event[0]).inline_keyboard[0])

    keyboard.append([
        InlineKeyboardButton(text="⬅️ Главное меню", callback_data="menu_back")
    ])

    await target.edit_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode="HTML",
    )


@router.message(F.text == "📅 Мероприятия")
async def legacy_events(message: Message):
    await message.answer(
        "Откройте /start, чтобы использовать обновлённое меню.",
        reply_markup=main_menu,
    )


@router.message(F.text == "💰 Цены")
async def legacy_prices(message: Message):
    await message.answer(
        "Откройте /start, чтобы использовать обновлённое меню.",
        reply_markup=main_menu,
    )


@router.message(F.text == "📞 Контакты")
async def legacy_contacts(message: Message):
    await message.answer(
        "Откройте /start, чтобы использовать обновлённое меню.",
        reply_markup=main_menu,
    )


@router.message(F.text == "❓ FAQ")
async def legacy_faq(message: Message):
    await message.answer(
        "Откройте /start, чтобы использовать обновлённое меню.",
        reply_markup=main_menu,
    )


@router.callback_query(F.data == "menu_prices")
async def menu_prices(callback: CallbackQuery):
    await callback.answer()
    await show_prices(callback.message)


@router.callback_query(F.data == "menu_contacts")
async def menu_contacts(callback: CallbackQuery):
    await callback.answer()
    await show_contacts(callback.message)


@router.callback_query(F.data == "menu_faq")
async def menu_faq(callback: CallbackQuery):
    await callback.answer()
    await show_faq(callback.message)


@router.callback_query(F.data == "menu_events")
async def menu_events(callback: CallbackQuery):
    await callback.answer()
    try:
        await show_events(callback.message)
    except Exception:
        await callback.message.edit_text(
            "⚠️ Не удалось загрузить мероприятия. Попробуйте ещё раз.",
            reply_markup=back_to_menu_keyboard(),
        )


@router.callback_query(F.data == "menu_back")
async def menu_back(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(
        "🌊 <b>Wild East Club</b>\n\n"
        "Стирая границы, создавая моменты.\n\n"
        "Выберите нужный раздел 👇",
        reply_markup=main_menu,
        parse_mode="HTML",
    )
