import logging

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import config
from database import Database


db = Database()
router = Router()
ADMIN_ID = config.owner_id
logger = logging.getLogger(__name__)


def admin_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📋 Заявки", callback_data="admin_bookings")],
            [InlineKeyboardButton(text="📅 Мероприятия", callback_data="admin_events")],
        ]
    )


def back_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_back")]
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
        "👨‍💼 Административная панель\n\nВыберите нужный раздел:",
        reply_markup=admin_keyboard(),
    )


async def booking_card_keyboard(booking):
    booking_id, event_id, telegram_id, full_name, phone, created_at, event_date, event_time, route_title, children, comment, status, max_places = booking
    buttons = []

    if status == "confirmed":
        buttons.append([InlineKeyboardButton(text="↩️ Вернуть в новые", callback_data=f"booking_status_new_{booking_id}")])
    elif status in ("cancelled", "canceled"):
        buttons.append([InlineKeyboardButton(text="↩️ Вернуть в новые", callback_data=f"booking_status_new_{booking_id}")])
    else:
        buttons.append([
            InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"booking_status_confirmed_{booking_id}"),
            InlineKeyboardButton(text="❌ Отменить", callback_data=f"booking_status_cancelled_{booking_id}"),
        ])

    phone_digits = "".join(ch for ch in phone if ch.isdigit())
    buttons.append([
        InlineKeyboardButton(text="📞 Позвонить", url=f"tel:+{phone_digits}"),
        InlineKeyboardButton(text="💬 Написать", url=f"tg://user?id={telegram_id}"),
    ])
    buttons.append([
        InlineKeyboardButton(text="⬅️ Предыдущая", callback_data=f"booking_prev_{booking_id}"),
        InlineKeyboardButton(text="Следующая ➡️", callback_data=f"booking_next_{booking_id}"),
    ])
    buttons.append([InlineKeyboardButton(text="🏠 Админ-панель", callback_data="admin_back")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def booking_status_label(status):
    return {
        "new": "🆕 Новая",
        "confirmed": "✅ Подтверждена",
        "cancelled": "❌ Отменена",
        "canceled": "❌ Отменена",
    }.get(status, status)


def format_booking_card(booking, booked_count, max_places):
    (
        booking_id, event_id, telegram_id, full_name, phone, created_at,
        event_date, event_time, route_title, children, comment, status, _max_places,
    ) = booking

    date_display = (
        f"{event_date[8:10]}.{event_date[5:7]}.{event_date[:4]}"
        if event_date else "—"
    )

    lines = [
        f"👤 <b>{full_name}</b>",
        "",
        f"📞 {phone}",
        f"🛶 {route_title or 'Маршрут не указан'}",
        f"📅 {date_display}",
        f"🕒 {event_time or '—'}",
        f"👶 Ребёнок: {'да' if children else 'нет'}",
    ]

    if comment:
        lines.append(f"💬 Комментарий: {comment}")

    lines.extend([
        "",
        f"{booking_status_label(status)}",
        "",
        f"<b>Заявки: {booked_count} / {max_places}</b>",
    ])
    return "\n".join(lines)


async def show_bookings(callback: CallbackQuery):
    bookings = await db.get_bookings()

    if not bookings:
        await callback.message.edit_text(
            "📋 <b>Заявки</b>\n\nЗаявок пока нет.",
            reply_markup=back_keyboard(),
            parse_mode="HTML",
        )
        return

    booking = bookings[0]
    booked_count, max_places = await db.get_event_booking_stats(booking[1])
    await callback.message.edit_text(
        format_booking_card(booking, booked_count, max_places),
        reply_markup=await booking_card_keyboard(booking),
        parse_mode="HTML",
    )


async def show_booking_by_id(callback: CallbackQuery, booking_id: int, direction=None):
    bookings = await db.get_bookings()
    index = next((i for i, item in enumerate(bookings) if item[0] == booking_id), None)

    if index is None:
        await callback.answer("⚠️ Заявка не найдена", show_alert=True)
        return

    if direction == "next":
        index = (index + 1) % len(bookings)
    elif direction == "prev":
        index = (index - 1) % len(bookings)

    booking = bookings[index]
    booked_count, max_places = await db.get_event_booking_stats(booking[1])
    await callback.message.edit_text(
        format_booking_card(booking, booked_count, max_places),
        reply_markup=await booking_card_keyboard(booking),
        parse_mode="HTML",
    )


async def show_events(callback: CallbackQuery):
    events = await db.get_events()
    keyboard = []

    for event in events:
        event_id, route_id, event_date, event_time, price, route_title, start_point, finish_point, meeting_point = event
        keyboard.append([
            InlineKeyboardButton(
                text=f"✏️ {event_date[8:10]}-{event_date[5:7]}-{event_date[:4]} {event_time} — {route_title}",
                callback_data=f"edit_event_{event_id}",
            )
        ])

    keyboard.append([
        InlineKeyboardButton(
            text="➕ Добавить мероприятие",
            callback_data="add_event",
        )
    ])
    keyboard.append([
        InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_back")
    ])

    await callback.message.edit_text(
        "📅 <b>Управление мероприятиями</b>\n\n"
        "Выберите мероприятие для редактирования или создайте новое:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "admin_back")
async def admin_back(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    await callback.answer()
    await callback.message.edit_text(
        "👨‍💼 Административная панель\n\nВыберите нужный раздел:",
        reply_markup=admin_keyboard(),
    )


@router.callback_query(F.data == "admin_bookings")
async def admin_bookings(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    await callback.answer()
    try:
        await show_bookings(callback)
    except Exception:
        logger.exception("Failed to load bookings")
        await callback.message.edit_text(
            "⚠️ Не удалось загрузить заявки. Ошибка записана в лог.",
            reply_markup=back_keyboard(),
        )


@router.callback_query(F.data.regexp(r"^booking_status_(new|confirmed|cancelled)_\d+$"))
async def booking_status(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    parts = callback.data.split("_")
    status = parts[2]
    booking_id = int(parts[3])

    await db.update_booking_status(booking_id, status)
    await callback.answer(
        "Заявка подтверждена" if status == "confirmed"
        else "Заявка отменена" if status == "cancelled"
        else "Заявка снова активна"
    )
    await show_booking_by_id(callback, booking_id)


@router.callback_query(F.data.regexp(r"^booking_(next|prev)_\d+$"))
async def booking_navigation(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    direction = callback.data.split("_")[1]
    booking_id = int(callback.data.split("_")[2])
    await callback.answer()
    await show_booking_by_id(callback, booking_id, direction)


@router.callback_query(F.data == "admin_events")
async def admin_events(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    await callback.answer()
    try:
        await show_events(callback)
    except Exception:
        logger.exception("Failed to load events")
        await callback.message.edit_text(
            "⚠️ Не удалось загрузить мероприятия. Ошибка записана в лог.",
            reply_markup=back_keyboard(),
        )


