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


@router.callback_query(F.data == "admin_event_cancel")
async def add_event_cancel(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    await callback.answer("Создание отменено")
    await state.clear()
    await callback.message.edit_text("📅 <b>Управление мероприятиями</b>\n\nСоздание мероприятия отменено.", parse_mode="HTML")
