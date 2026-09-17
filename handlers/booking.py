from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from config import config
from states.booking import BookingState
from database import Database
from keyboards.booking import phone_keyboard
from keyboards.booking_confirm import booking_confirm_keyboard

router = Router()
db = Database()
ADMIN_ID = config.owner_id


def booking_keyboard(event_id):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Записаться",
                    callback_data=f"book_{event_id}"
                )
            ]
        ]
    )


def event_text(event):
    (
        _event_id,
        event_date,
        event_time,
        price,
        route_title,
        start_point,
        finish_point,
    ) = event

    return (
        "🌊 <b>Вы выбрали мероприятие</b>\n\n"
        f"🛶 <b>{route_title}</b>\n"
        f"📅 {event_date}\n"
        f"🕐 {event_time}\n"
        f"📍 {start_point} → {finish_point}\n"
        f"💰 <b>{price} ₽</b>\n\n"
        "👤 Теперь введите ваше имя:"
    )


@router.callback_query(F.data.startswith("book_"))
async def booking(callback: CallbackQuery, state: FSMContext):
    await callback.answer()

    event_id = int(callback.data.split("_", 1)[1])
    event = await db.get_event_info(event_id)

    if not event:
        await callback.message.answer(
            "⚠️ Это мероприятие больше недоступно.\n\n"
            "Откройте раздел «Мероприятия» и выберите другое."
        )
        return

    await state.update_data(event_id=event_id)
    await callback.message.answer(event_text(event), parse_mode="HTML")
    await state.set_state(BookingState.waiting_name)


@router.message(BookingState.waiting_name)
async def get_name(message: Message, state: FSMContext):
    full_name = (message.text or "").strip()

    if not full_name:
        await message.answer("Пожалуйста, введите ваше имя.")
        return

    await state.update_data(full_name=full_name)
    await message.answer(
        "📞 Отправьте номер телефона кнопкой ниже "
        "или введите его вручную в формате 7XXXXXXXXX:",
        reply_markup=phone_keyboard()
    )
    await state.set_state(BookingState.waiting_phone)


@router.message(BookingState.waiting_phone)
async def get_phone(message: Message, state: FSMContext):
    if message.contact:
        phone = message.contact.phone_number
    else:
        phone = (message.text or "").strip()

    if not phone:
        await message.answer(
            "Пожалуйста, отправьте номер телефона или введите его вручную."
        )
        return

    await state.update_data(phone=phone)
    data = await state.get_data()
    event = await db.get_event_info(data.get("event_id"))

    event_info = ""
    if event:
        (
            _event_id,
            event_date,
            event_time,
            price,
            route_title,
            start_point,
            finish_point,
        ) = event
        event_info = (
            f"🛶 Маршрут: {route_title}\n"
            f"📅 Дата: {event_date}\n"
            f"🕐 Время: {event_time}\n"
            f"📍 {start_point} → {finish_point}\n"
            f"💰 Стоимость: {price} ₽\n\n"
        )

    await message.answer(
        "📋 <b>Проверьте данные заявки</b>\n\n"
        f"{event_info}"
        f"👤 Имя: {data['full_name']}\n"
        f"📞 Телефон: {phone}\n\n"
        "Всё верно?",
        reply_markup=booking_confirm_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "booking_confirm")
async def booking_confirm(callback: CallbackQuery, state: FSMContext):
    await callback.answer()

    data = await state.get_data()
    event_id = data.get("event_id")
    full_name = data.get("full_name")
    phone = data.get("phone")

    if not event_id or not full_name or not phone:
        await callback.message.answer(
            "❌ Не удалось получить данные заявки.\n"
            "Пожалуйста, начните запись заново."
        )
        await state.clear()
        return

    await callback.message.edit_text(
        "⏳ Заявка отправляется...\n\n"
        "Пожалуйста, подождите несколько секунд."
    )

    try:
        await db.add_booking(
            telegram_id=callback.from_user.id,
            event_id=event_id,
            full_name=full_name,
            phone=phone,
        )

        event = await db.get_event_info(event_id)

        if event:
            (
                _event_id,
                event_date,
                event_time,
                price,
                route_title,
                _start_point,
                _finish_point,
            ) = event

            try:
                await callback.bot.send_message(
                    ADMIN_ID,
                    "🔔 НОВАЯ ЗАЯВКА!\n\n"
                    f"📅 Дата: {event_date}\n"
                    f"🕐 Время: {event_time}\n"
                    f"🛶 Маршрут: {route_title}\n"
                    f"💰 Стоимость: {price} ₽\n\n"
                    f"👤 Имя: {full_name}\n"
                    f"📞 Телефон: {phone}\n"
                )
            except Exception:
                pass

        await callback.message.edit_text(
            "🎉 <b>Заявка принята!</b>\n\n"
            "Мы приняли вашу заявку на САП-сплав с командой Wild East Club.\n\n"
            "В ближайшее время организатор свяжется с вами для подтверждения участия.\n\n"
            "📞 +7 924 416-00-83",
            parse_mode="HTML",
        )
    except Exception:
        await callback.message.edit_text(
            "⚠️ Не удалось отправить заявку.\n\n"
            "Попробуйте ещё раз через несколько секунд."
        )
        raise
    finally:
        await state.clear()


@router.callback_query(F.data == "booking_cancel")
async def booking_cancel(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()

    await callback.message.edit_text(
        "❌ Заявка отменена.\n\n"
        "Если захотите записаться — откройте раздел «Мероприятия» ещё раз."
    )
