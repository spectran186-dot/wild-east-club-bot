from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from database import Database
from handlers.booking import booking_keyboard, cache_event
from keyboards.user import main_menu, back_to_menu_keyboard


db = Database()
router = Router()


async def show_prices(message: Message):
    await message.answer(
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


async def show_contacts(message: Message):
    await message.answer(
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


async def show_faq(message: Message):
    await message.answer(
        "❓ <b>Частые вопросы</b>\n\n"
        "• Нужен ли опыт? — Нет.\n"
        "• Выдают ли жилет? — Да.\n"
        "• Можно с ребёнком? — Да.",
        reply_markup=back_to_menu_keyboard(),
        parse_mode="HTML",
    )


async def show_events(message: Message):
    events_list = await db.get_events()

    if not events_list:
        await message.answer(
            "📅 <b>Мероприятия</b>\n\nПока мероприятий нет.",
            reply_markup=back_to_menu_keyboard(),
            parse_mode="HTML",
        )
        return

    # Заголовок выводим отдельным сообщением.
    await message.answer(
        "📅 <b>Мероприятия</b>",
        parse_mode="HTML",
    )

    # Каждое мероприятие — отдельным сообщением.
    # Поэтому кнопка «Записаться» находится непосредственно под своим мероприятием.
    for event in events_list:
        event_id, route_id, event_date, event_time, price, route_title, start_point, finish_point, meeting_point = event
        cache_event(event)

        event_text = (
            "🌊 <b>САП-сплав</b>\n"
            f"🛶 <b>{route_title}</b>\n"
            f"📅 {event_date[8:10]}.{event_date[5:7]}.{event_date[:4]}\n"
            f"🕒 {event_time}\n"
            f"📍 {meeting_point or start_point}\n"
            f"💰 {price} ₽"
        )

        await message.answer(
            event_text,
            reply_markup=booking_keyboard(event_id),
            parse_mode="HTML",
        )

    await message.answer(
        "Выберите мероприятие для записи:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="⬅️ Главное меню",
                        callback_data="menu_back",
                    )
                ]
            ]
        ),
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
        await callback.message.answer(
            "⚠️ Не удалось загрузить мероприятия. Попробуйте ещё раз.",
            reply_markup=back_to_menu_keyboard(),
        )


@router.callback_query(F.data == "menu_back")
async def menu_back(callback: CallbackQuery):
    await callback.answer()
    try:
        await callback.message.delete()
    except Exception:
        pass
