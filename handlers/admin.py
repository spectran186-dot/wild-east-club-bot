from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import config
from database import Database


db = Database()
router = Router()
ADMIN_ID = config.owner_id


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


def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


@router.message(Command("admin"))
async def admin_panel(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет доступа к административной панели.")
        return

    await message.answer(
        "👨‍💼 Административная панель\n\n"
        "Выберите нужный раздел:",
        reply_markup=admin_keyboard()
    )


@router.callback_query(F.data == "admin_bookings")
async def admin_bookings(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    # Отвечаем Telegram немедленно. Никаких DB/API операций до callback.answer().
    await callback.answer("Загружаю заявки…")

    try:
        bookings = await db.get_bookings()
    except Exception:
        import logging
        logging.getLogger(__name__).exception("Failed to load bookings")
        await callback.message.answer("⚠️ Не удалось загрузить заявки. Ошибка записана в лог.")
        return

    if not bookings:
        await callback.message.answer("📋 Заявок пока нет.")
        return

    lines = ["📋 <b>Заявки</b>", ""]

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

        lines.extend([
            f"🆔 Заявка №{booking_id}",
            f"👤 {full_name}",
            f"📞 +{phone}",
            f"📅 {event_date}  {event_time}",
            f"🛶 {route_title}",
            f"🕐 Создана: {created_at}",
            "──────────────",
        ])

    text = "\n".join(lines)

    for start in range(0, len(text), 4000):
        await callback.message.answer(
            text[start:start + 4000],
            parse_mode="HTML"
        )


@router.callback_query(F.data == "admin_events")
async def admin_events(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    # Отвечаем Telegram немедленно. Никаких DB/API операций до callback.answer().
    await callback.answer("Загружаю мероприятия…")

    try:
        events = await db.get_events()
    except Exception:
        import logging
        logging.getLogger(__name__).exception("Failed to load events")
        await callback.message.answer("⚠️ Не удалось загрузить мероприятия. Ошибка записана в лог.")
        return

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
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("edit_event_"))
async def edit_event_placeholder(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    await callback.answer(
        "✏️ Редактирование мероприятий пока не реализовано.",
        show_alert=True
    )


@router.callback_query(F.data == "add_event")
async def add_event_placeholder(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    await callback.answer(
        "➕ Создание мероприятий пока не реализовано.",
        show_alert=True
    )
