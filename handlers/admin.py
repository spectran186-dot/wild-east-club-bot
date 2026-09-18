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
            [InlineKeyboardButton(text="📊 Отчёты", callback_data="admin_reports")],
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

    if status != "new":
        return InlineKeyboardMarkup(inline_keyboard=[])

    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="✅ Подтвердить",
                callback_data=f"booking_status_confirmed_{booking_id}",
            ),
            InlineKeyboardButton(
                text="❌ Отменить",
                callback_data=f"booking_status_cancelled_{booking_id}",
            ),
        ]
    ])


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

    # Группируем заявки по мероприятию
    events = {}
    for booking in bookings:
        event_id = booking[1]
        events.setdefault(event_id, []).append(booking)

    keyboard = []
    for event_id, event_bookings in events.items():
        first = event_bookings[0]
        event_date, event_time, route_title = first[6], first[7], first[8]
        date_display = (
            f"{event_date[8:10]}.{event_date[5:7]}.{event_date[:4]}"
            if event_date else "—"
        )
        booked_count, max_places = await db.get_event_booking_stats(event_id)
        keyboard.append([
            InlineKeyboardButton(
                text=f"📅 {date_display[:5]} · {event_time or '—'}\n🛶 {route_title or 'Маршрут'} · {booked_count}/{max_places}",
                callback_data=f"booking_event_{event_id}",
            )
        ])

    keyboard.append([
        InlineKeyboardButton(text="🏠 Админ-панель", callback_data="admin_back")
    ])

    await callback.message.edit_text(
        "📋 <b>Заявки</b>\n\nВыберите мероприятие:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode="HTML",
    )


async def show_event_bookings(callback: CallbackQuery, event_id: int, page: int = 0):
    bookings = [b for b in await db.get_bookings() if b[1] == event_id]
    if not bookings:
        await callback.answer("⚠️ Заявок по мероприятию нет", show_alert=True)
        return

    first = bookings[0]
    event_date, event_time, route_title = first[6], first[7], first[8]
    date_display = f"{event_date[8:10]}.{event_date[5:7]}.{event_date[:4]}" if event_date else "—"
    booked_count, max_places = await db.get_event_booking_stats(event_id)

    page_size = 10
    total_pages = max(1, (len(bookings) + page_size - 1) // page_size)
    page = max(0, min(page, total_pages - 1))
    page_bookings = bookings[page * page_size:(page + 1) * page_size]

    await callback.message.edit_text(
        f"📋 <b>{route_title or 'Мероприятие'}</b>\n"
        f"📅 {date_display}  🕒 {event_time or '—'}\n"
        f"Заявок: <b>{booked_count} / {max_places}</b>\n"
        f"Страница <b>{page + 1}/{total_pages}</b>",
        parse_mode="HTML",
    )

    for booking in page_bookings:
        (
            booking_id, _event_id, _telegram_id, full_name, phone, _created_at,
            _event_date, _event_time, _route_title, children, comment, status, _max_places,
        ) = booking
        lines = [
            f"👤 <b>{full_name}</b>", "", f"📞 {phone}",
            f"🛶 {route_title or 'Маршрут не указан'}",
            f"📅 {date_display}", f"🕒 {event_time or '—'}",
            f"👶 Ребёнок: {'да' if children else 'нет'}",
        ]
        if comment:
            lines.append(f"💬 Комментарий: {comment}")
        lines.extend(["", booking_status_label(status), "", f"<b>Заявки: {booked_count} / {max_places}</b>"])
        await callback.message.answer(
            "\n".join(lines),
            reply_markup=await booking_card_keyboard(booking),
            parse_mode="HTML",
        )

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️ Предыдущая", callback_data=f"booking_page_{event_id}_{page - 1}"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(text="Следующая ➡️", callback_data=f"booking_page_{event_id}_{page + 1}"))
    keyboard = [nav] if nav else []
    keyboard.append([InlineKeyboardButton(text="⬅️ Вернуться назад", callback_data="admin_bookings")])
    await callback.message.answer(
        f"Страница {page + 1} из {total_pages}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
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


@router.callback_query(F.data.regexp(r"^booking_page_\d+_\d+$"))
async def booking_page(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    parts = callback.data.split("_")
    event_id, page = int(parts[2]), int(parts[3])
    await callback.answer()
    try:
        await show_event_bookings(callback, event_id, page)
    except Exception:
        logger.exception("Failed to load booking page")
        await callback.message.edit_text("⚠️ Не удалось загрузить страницу заявок.", reply_markup=back_keyboard())

@router.callback_query(F.data.regexp(r"^booking_event_\d+$"))
async def booking_event(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    event_id = int(callback.data.split("_")[2])
    await callback.answer()
    try:
        await show_event_bookings(callback, event_id)
    except Exception:
        logger.exception("Failed to load event bookings")
        await callback.message.edit_text(
            "⚠️ Не удалось загрузить заявки мероприятия.",
            reply_markup=back_keyboard(),
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


@router.callback_query(F.data.regexp(r"^booking_status_(confirmed|cancelled)_\d+$"))
async def booking_status(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    parts = callback.data.split("_")
    status = parts[2]
    booking_id = int(parts[3])

    if status == "cancelled":
        await db.delete_booking(booking_id)
        await callback.answer("Заявка удалена")
        # После удаления карточка больше не нужна.
        try:
            await callback.message.delete()
        except Exception:
            logger.exception("Failed to delete cancelled booking card")
    else:
        await db.update_booking_status(booking_id, status)
        await callback.answer("Заявка подтверждена")

        # Карточка остаётся на экране, но кнопки подтверждения/отмены убираются.
        try:
            await callback.message.edit_reply_markup(
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[])
            )
        except Exception:
            logger.exception("Failed to update confirmed booking card")


@router.callback_query(F.data == "admin_reports")
async def admin_reports(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    bookings = await db.get_bookings()
    if not bookings:
        await callback.answer()
        await callback.message.edit_text(
            "📊 <b>Отчёты</b>\n\nЗаявок пока нет.",
            reply_markup=back_keyboard(),
            parse_mode="HTML",
        )
        return

    routes = {}
    for booking in bookings:
        route_title = booking[8] or "Маршрут не указан"
        routes.setdefault(route_title, []).append(booking)

    keyboard = []
    for route_title, route_bookings in sorted(routes.items()):
        people = len(route_bookings) + sum(int(b[9] or 0) for b in route_bookings)
        boards = len(route_bookings)
        revenue = 0
        for booking in route_bookings:
            event = await db.get_event(booking[1])
            price = int(event[3] or 0) if event else 0
            revenue += price + int(booking[9] or 0) * 500
        keyboard.append([
            InlineKeyboardButton(
                text=f"🛶 {route_title}\n👥 {people} чел. · 🏄 {boards} досок · 💰 {revenue:,} ₽".replace(",", " "),
                callback_data=f"report_route_{route_bookings[0][1]}",
            )
        ])

    keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_back")])
    await callback.answer()
    await callback.message.edit_text(
        "📊 <b>Отчёты</b>\n\nВыберите маршрут:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode="HTML",
    )

@router.callback_query(F.data.regexp(r"^report_route_\d+$"))
async def report_route(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    event_id = int(callback.data.split("_")[2])
    all_bookings = await db.get_bookings()
    selected = [b for b in all_bookings if b[1] == event_id]
    if not selected:
        await callback.answer("⚠️ Заявок по маршруту нет", show_alert=True)
        return

    route_title = selected[0][8] or "Маршрут не указан"
    route_bookings = [b for b in all_bookings if (b[8] or "Маршрут не указан") == route_title]
    total_people = len(route_bookings) + sum(int(b[9] or 0) for b in route_bookings)
    total_boards = len(route_bookings)
    total_revenue = 0
    lines = [f"📊 <b>Отчёт: {route_title}</b>", ""]

    events = {}
    for booking in route_bookings:
        events.setdefault(booking[1], []).append(booking)

    for current_event_id, event_bookings in sorted(events.items(), key=lambda item: (item[1][0][6] or "", item[1][0][7] or "")):
        event = await db.get_event(current_event_id)
        price = int(event[3] or 0) if event else 0
        first = event_bookings[0]
        date_display = f"{first[6][8:10]}.{first[6][5:7]}.{first[6][:4]}" if first[6] else "—"
        event_time = first[7] or "—"
        lines.append(f"<b>📅 {date_display} · {event_time}</b>")
        for booking in event_bookings:
            name = booking[3] or "—"
            phone = booking[4] or "—"
            children = int(booking[9] or 0)
            booking_revenue = price + children * 500
            total_revenue += booking_revenue
            lines.append(f"• {name} — {phone} · 👥 {1 + children} · 🏄 1 · 💰 {booking_revenue:,} ₽".replace(",", " "))
        lines.append("")

    lines.extend([
        "━━━━━━━━━━━━━━",
        f"👥 <b>Людей: {total_people}</b>",
        f"🏄 <b>Досок: {total_boards}</b>",
        f"💰 <b>Выручка: {total_revenue:,} ₽</b>".replace(",", " "),
    ])

    text_report = "\n".join(lines)
    chunks = []
    current = ""
    for line in text_report.split("\n"):
        if current and len(current) + len(line) + 1 > 3900:
            chunks.append(current)
            current = ""
        current += ("\n" if current else "") + line
    if current:
        chunks.append(current)

    await callback.answer()
    await callback.message.edit_text(
        chunks[0],
        parse_mode="HTML",
        reply_markup=back_keyboard() if len(chunks) == 1 else None,
    )
    for chunk in chunks[1:]:
        await callback.message.answer(chunk, parse_mode="HTML")
    if len(chunks) > 1:
        await callback.message.answer("Навигация:", reply_markup=back_keyboard())


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


