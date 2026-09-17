from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import Database
db = Database()
router = Router()

ADMIN_ID = 323262204


def admin_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📋 Заявки",
                    callback_data="admin_bookings"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📅 Мероприятия",
                    callback_data="admin_events"
                )
            ]
        ]
    )


@router.message(Command("admin"))
async def admin_panel(message: Message):

    if message.from_user.id != ADMIN_ID:
        await message.answer(
            "⛔ У вас нет доступа к административной панели."
        )
        return

    await message.answer(
        "👨‍💼 Административная панель\n\n"
        "Выберите нужный раздел:",
        reply_markup=admin_keyboard()
    )

@router.callback_query(lambda callback: callback.data == "admin_bookings")
async def admin_bookings(callback: CallbackQuery):

    if callback.from_user.id != ADMIN_ID:
        await callback.answer(
            "⛔ Нет доступа",
            show_alert=True
        )
        return

    bookings = db.get_bookings()

    if not bookings:
        await callback.message.answer(
            "📋 Заявок пока нет."
        )
        await callback.answer()
        return

    text = "📋 <b>Заявки</b>\n\n"

    for booking in bookings:
        (
            booking_id,
            full_name,
            phone,
            created_at,
            event_date,
            event_time,
            route_title
        ) = booking

        text += (
            f"🆔 Заявка №{booking_id}\n"
            f"👤 {full_name}\n"
            f"📞 +{phone}\n"
            f"📅 {event_date}  {event_time}\n"
            f"🛶 {route_title}\n"
            f"🕐 Создана: {created_at}\n"
            f"──────────────\n"
        )

    await callback.message.answer(
        text,
        parse_mode="HTML"
    )

    await callback.answer()

@router.callback_query(lambda callback: callback.data == "admin_events")
async def admin_events(callback: CallbackQuery):

    if callback.from_user.id != ADMIN_ID:
        await callback.answer(
            "⛔ Нет доступа",
            show_alert=True
        )
        return

    events = db.get_events()

    keyboard = []

    for event in events:
        event_id, route_id, event_date, event_time, price = event

        keyboard.append([
            InlineKeyboardButton(
                text=f"✏️ {event_date} {event_time}",
                callback_data=f"edit_event_{event_id}"
            )
        ])

    keyboard.append([
        InlineKeyboardButton(
            text="➕ Добавить мероприятие",
            callback_data="add_event"
        )
    ])

    await callback.message.answer(
        "📅 <b>Управление мероприятиями</b>\n\n"
        "Выберите мероприятие для редактирования "
        "или создайте новое:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=keyboard
        ),
        parse_mode="HTML"
    )

    await callback.answer()