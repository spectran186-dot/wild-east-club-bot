from datetime import datetime

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from config import config
from database import Database
from states.admin_event import AdminEventState

router = Router()
db = Database()
ADMIN_ID = config.owner_id


def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


def cancel_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Отмена", callback_data="admin_event_cancel")]])


def route_keyboard(routes):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"🛶 {route[1]}", callback_data=f"admin_event_route_{route[0]}")]
            for route in routes
        ] + [[InlineKeyboardButton(text="❌ Отмена", callback_data="admin_event_cancel")]]
    )


@router.callback_query(F.data == "add_event")
async def add_event_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    await callback.answer()
    routes = await db.get_routes()
    if not routes:
        await callback.message.edit_text("⚠️ Нет доступных маршрутов.")
        return
    await state.clear()
    await callback.message.edit_text(
        "➕ <b>Добавление мероприятия</b>\n\nШаг 1 из 5 — выберите маршрут:",
        reply_markup=route_keyboard(routes),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("admin_event_route_"))
async def add_event_route(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    await callback.answer()
    route_id = int(callback.data.rsplit("_", 1)[1])
    routes = await db.get_routes()
    route = next((item for item in routes if item[0] == route_id), None)
    if not route:
        await callback.message.edit_text("⚠️ Маршрут не найден.")
        return
    await state.update_data(route_id=route_id, route_title=route[1], default_price=route[4])
    await state.set_state(AdminEventState.waiting_date)
    await callback.message.edit_text(
        f"➕ <b>Добавление мероприятия</b>\n\n"
        f"Маршрут: <b>{route[1]}</b>\n\n"
        "Шаг 2 из 5 — введите дату в формате <code>ДД.ММ.ГГГГ</code>:",
        reply_markup=cancel_keyboard(), parse_mode="HTML",
    )


@router.message(AdminEventState.waiting_date)
async def add_event_date(message: Message, state: FSMContext):
    try:
        date_value = datetime.strptime(message.text.strip(), "%d.%m.%Y").date()
    except (ValueError, AttributeError):
        await message.answer("⚠️ Неверная дата. Используйте формат ДД.ММ.ГГГГ", reply_markup=cancel_keyboard())
        return
    await state.update_data(event_date=date_value.isoformat())
    await state.set_state(AdminEventState.waiting_time)
    await message.answer("Шаг 3 из 5 — введите время мероприятия, например <code>10:00-13:00</code>:", reply_markup=cancel_keyboard(), parse_mode="HTML")


@router.message(AdminEventState.waiting_time)
async def add_event_time(message: Message, state: FSMContext):
    value = (message.text or "").strip()
    if not value or len(value) > 30:
        await message.answer("⚠️ Введите корректное время, например 10:00-13:00.", reply_markup=cancel_keyboard())
        return
    await state.update_data(event_time=value)
    await state.set_state(AdminEventState.waiting_price)
    data = await state.get_data()
    await message.answer(f"Шаг 4 из 5 — введите цену в рублях. По умолчанию для маршрута: <b>{data['default_price']} ₽</b>.", reply_markup=cancel_keyboard(), parse_mode="HTML")


@router.message(AdminEventState.waiting_price)
async def add_event_price(message: Message, state: FSMContext):
    try:
        price = int((message.text or "").strip().replace(" ", "").replace("₽", ""))
        if price < 0:
            raise ValueError
    except ValueError:
        await message.answer("⚠️ Цена должна быть целым числом в рублях.", reply_markup=cancel_keyboard())
        return
    await state.update_data(price=price)
    await state.set_state(AdminEventState.waiting_meeting_point)
    await message.answer("Шаг 5 из 5 — введите точку встречи:", reply_markup=cancel_keyboard())


@router.message(AdminEventState.waiting_meeting_point)
async def add_event_meeting_point(message: Message, state: FSMContext):
    meeting_point = (message.text or "").strip()
    if not meeting_point:
        await message.answer("⚠️ Точка встречи не может быть пустой.", reply_markup=cancel_keyboard())
        return
    data = await state.get_data()
    event_id = await db.add_event(data["route_id"], data["event_date"], data["event_time"], data["price"], meeting_point)
    await state.clear()
    date_display = datetime.strptime(data["event_date"], "%Y-%m-%d").strftime("%d.%m.%Y")
    await message.answer(
        "✅ <b>Мероприятие сохранено!</b>\n\n"
        f"🆔 №{event_id}\n"
        f"🛶 {data['route_title']}\n"
        f"📅 {date_display}\n"
        f"🕒 {data['event_time']}\n"
        f"💰 {data['price']} ₽\n"
        f"📍 {meeting_point}",
        parse_mode="HTML",
    )

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
    keyboard.append([InlineKeyboardButton(text="➕ Добавить мероприятие", callback_data="add_event")])
    keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_back")])
    await message.answer(
        "📅 <b>Управление мероприятиями</b>\n\n"
        "Выберите мероприятие для редактирования или создайте новое:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "admin_event_cancel")
async def add_event_cancel(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    await callback.answer("Создание отменено")
    await state.clear()
    await callback.message.edit_text("📅 <b>Управление мероприятиями</b>\n\nСоздание мероприятия отменено.", parse_mode="HTML")



def edit_fields_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛶 Маршрут", callback_data="edit_field_route")],
        [InlineKeyboardButton(text="📅 Дата", callback_data="edit_field_date")],
        [InlineKeyboardButton(text="🕒 Время", callback_data="edit_field_time")],
        [InlineKeyboardButton(text="💰 Цена", callback_data="edit_field_price")],
        [InlineKeyboardButton(text="📍 Точка встречи", callback_data="edit_field_meeting")],
        [InlineKeyboardButton(text="🗑 Удалить мероприятие", callback_data="delete_event")],
        [InlineKeyboardButton(text="⬅️ К списку мероприятий", callback_data="edit_event_back")],
    ])


def edit_event_text(data):
    return (
        "✏️ <b>Редактирование мероприятия</b>\n\n"
        f"🆔 №{data['edit_event_id']}\n"
        f"🛶 {data['route_title']}\n"
        f"📅 {data['event_date'][8:10]}.{data['event_date'][5:7]}.{data['event_date'][:4]}\n"
        f"🕒 {data['event_time']}\n"
        f"💰 {data['price']} ₽\n"
        f"📍 {data['meeting_point']}\n\n"
        "Выберите, что изменить:"
    )


async def show_edit_menu(message, state):
    data = await state.get_data()
    await message.edit_text(
        edit_event_text(data),
        reply_markup=edit_fields_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data.regexp(r"^edit_event_\d+$"))
async def edit_event_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    await callback.answer()
    event_id = int(callback.data.split("_", 2)[2])
    event = await db.get_event_full(event_id)
    if not event:
        await callback.message.edit_text("⚠️ Мероприятие не найдено или уже недоступно.")
        return
    (
        _event_id, route_id, event_date, event_time, price,
        route_title, start_point, _finish_point, meeting_point,
    ) = event
    await state.clear()
    await state.update_data(
        edit_event_id=event_id,
        route_id=route_id,
        route_title=route_title,
        event_date=event_date,
        event_time=event_time,
        price=price,
        meeting_point=meeting_point or start_point,
    )
    await callback.message.edit_text(
        edit_event_text(await state.get_data()),
        reply_markup=edit_fields_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "edit_field_route")
async def edit_field_route(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    await callback.answer()
    routes = await db.get_routes()
    await state.set_state(AdminEventState.edit_waiting_route)
    await callback.message.edit_text(
        "🛶 <b>Выберите новый маршрут:</b>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"🛶 {r[1]}", callback_data=f"edit_route_{r[0]}")] for r in routes
        ] + [[InlineKeyboardButton(text="⬅️ Назад", callback_data="edit_menu")]]),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("edit_route_"))
async def edit_route_select(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    await callback.answer()
    route_id = int(callback.data.rsplit("_", 1)[1])
    route = next((r for r in await db.get_routes() if r[0] == route_id), None)
    if not route:
        await callback.message.edit_text("⚠️ Маршрут не найден.")
        return
    await db.update_event(
        (await state.get_data())["edit_event_id"], route_id,
        (await state.get_data())["event_date"], (await state.get_data())["event_time"],
        (await state.get_data())["price"], (await state.get_data())["meeting_point"],
    )
    await state.update_data(route_id=route_id, route_title=route[1])
    await state.set_state(AdminEventState.edit_waiting_route)
    await show_edit_menu(callback.message, state)


async def save_edit_field(message, state, field, value):
    data = await state.get_data()
    event_id = data.get("edit_event_id")
    if not event_id:
        await state.clear()
        await message.answer("⚠️ Мероприятие не найдено. Начните редактирование заново.")
        return

    data[field] = value
    await db.update_event(
        event_id, data["route_id"], data["event_date"], data["event_time"],
        data["price"], data["meeting_point"],
    )
    await state.update_data(**{field: value})
    await state.set_state(AdminEventState.edit_waiting_route)

    updated_data = await state.get_data()
    await message.answer(
        "✅ <b>Изменение сохранено.</b>\n\n"
        + edit_event_text(updated_data),
        reply_markup=edit_fields_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "edit_field_date")
async def edit_field_date(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(AdminEventState.edit_waiting_date)
    await callback.message.edit_text("📅 Введите новую дату: <code>ДД.ММ.ГГГГ</code>", reply_markup=cancel_keyboard(), parse_mode="HTML")


@router.message(AdminEventState.edit_waiting_date)
async def edit_event_date(message: Message, state: FSMContext):
    try:
        value = datetime.strptime((message.text or "").strip(), "%d.%m.%Y").date().isoformat()
    except (ValueError, AttributeError):
        await message.answer("⚠️ Неверная дата. Используйте ДД.ММ.ГГГГ.", reply_markup=cancel_keyboard())
        return
    await save_edit_field(message, state, "event_date", value)


@router.callback_query(F.data == "edit_field_time")
async def edit_field_time(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(AdminEventState.edit_waiting_time)
    await callback.message.edit_text("🕒 Введите новое время, например <code>10:00-13:00</code>:", reply_markup=cancel_keyboard(), parse_mode="HTML")


@router.message(AdminEventState.edit_waiting_time)
async def edit_event_time(message: Message, state: FSMContext):
    value = (message.text or "").strip()
    if not value or len(value) > 30:
        await message.answer("⚠️ Введите корректное время.", reply_markup=cancel_keyboard())
        return
    await save_edit_field(message, state, "event_time", value)


@router.callback_query(F.data == "edit_field_price")
async def edit_field_price(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(AdminEventState.edit_waiting_price)
    await callback.message.edit_text("💰 Введите новую цену в рублях:", reply_markup=cancel_keyboard())


@router.message(AdminEventState.edit_waiting_price)
async def edit_event_price(message: Message, state: FSMContext):
    try:
        value = int((message.text or "").strip().replace(" ", "").replace("₽", ""))
        if value < 0:
            raise ValueError
    except ValueError:
        await message.answer("⚠️ Цена должна быть целым числом.", reply_markup=cancel_keyboard())
        return
    await save_edit_field(message, state, "price", value)


@router.callback_query(F.data == "edit_field_meeting")
async def edit_field_meeting(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(AdminEventState.edit_waiting_meeting_point)
    await callback.message.edit_text("📍 Введите новую точку встречи:", reply_markup=cancel_keyboard())


@router.message(AdminEventState.edit_waiting_meeting_point)
async def edit_event_meeting_point(message: Message, state: FSMContext):
    value = (message.text or "").strip()
    if not value:
        await message.answer("⚠️ Точка встречи не может быть пустой.", reply_markup=cancel_keyboard())
        return
    await save_edit_field(message, state, "meeting_point", value)


@router.callback_query(F.data == "edit_menu")
async def edit_menu(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await show_edit_menu(callback.message, state)


@router.callback_query(F.data == "edit_event_back")
async def edit_event_back(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    await callback.answer()
    await state.clear()

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


@router.callback_query(F.data == "delete_event")
async def delete_event_confirm(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    await callback.message.edit_text(
        f"⚠️ <b>Удалить мероприятие №{data.get('edit_event_id')}?</b>\n\n"
        "Заявки участников сохранятся, но мероприятие исчезнет из активного списка.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🗑 Да, удалить", callback_data="delete_event_yes")],
            [InlineKeyboardButton(text="⬅️ Отмена", callback_data="edit_menu")],
        ]),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "delete_event_yes")
async def delete_event_yes(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    await callback.answer("Мероприятие удалено")
    data = await state.get_data()
    event_id = data.get("edit_event_id")
    if event_id:
        await db.delete_event(event_id)
    await state.clear()

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
