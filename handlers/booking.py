from aiogram import Router, F
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.fsm.context import FSMContext

from states.booking import BookingState

from database import Database

from keyboards.booking import phone_keyboard
from keyboards.booking_confirm import booking_confirm_keyboard

router = Router()
db = Database()
ADMIN_ID = 323262204

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


@router.callback_query(F.data.startswith("book_"))
async def booking(callback: CallbackQuery, state: FSMContext):

    event_id = int(callback.data.split("_")[1])

    # Сохраняем ID мероприятия
    await state.update_data(event_id=event_id)

    await callback.message.answer(
        "👤 Введите ваше имя:"
    )

    await state.set_state(BookingState.waiting_name)

    await callback.answer()

@router.message(BookingState.waiting_name)
async def get_name(message: Message, state: FSMContext):

    full_name = message.text.strip()

    if not full_name:
        await message.answer(
            "Пожалуйста, введите ваше имя."
        )
        return

    await state.update_data(
        full_name=full_name
    )

    await message.answer(
        "📞 Отправьте номер телефона кнопкой ниже "
        "или введите его вручную в формате 7XXXXXXXXX:",
        reply_markup=phone_keyboard()
    )

    await state.set_state(
        BookingState.waiting_phone
    )

@router.message(BookingState.waiting_phone)
async def get_phone(message: Message, state: FSMContext):

    if message.contact:
        phone = message.contact.phone_number
    else:
        phone = message.text.strip() if message.text else ""

    if not phone:
        await message.answer(
            "Пожалуйста, отправьте номер телефона "
            "или введите его вручную."
        )
        return

    await state.update_data(
        phone=phone
    )

    data = await state.get_data()

    await message.answer(
    "📋 Проверьте данные заявки:\n\n"
    f"👤 Имя: {data['full_name']}\n"
    f"📞 Телефон: {phone}\n\n"
    "Всё верно?",
    reply_markup=booking_confirm_keyboard()
   )
@router.callback_query(F.data == "booking_confirm")
async def booking_confirm(
    callback: CallbackQuery,
    state: FSMContext
):
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
        await callback.answer()
        return

    # Сохраняем заявку в базу
    db.add_booking(
        telegram_id=callback.from_user.id,
        event_id=event_id,
        full_name=full_name,
        phone=phone
    )

    # Получаем информацию о мероприятии
    event = db.get_event_info(event_id)

    # Уведомление организатору
    if event:
        (
            event_date,
            event_time,
            route_title
        ) = event

        await callback.bot.send_message(
            ADMIN_ID,
            "🔔 НОВАЯ ЗАЯВКА!\n\n"
            f"📅 Дата: {event_date}\n"
            f"🕐 Время: {event_time}\n"
            f"🛶 Маршрут: {route_title}\n\n"
            f"👤 Имя: {full_name}\n"
            f"📞 Телефон: {phone}\n"
        )

    # Ответ туристу
    await callback.message.answer(
        "🎉 Спасибо!\n\n"
        "Мы приняли вашу заявку на САП-сплав "
        "с командой Wild East Club!\n\n"
        "Будем рады видеть вас на старте. 😉\n\n"
        "В ближайшее время организатор свяжется "
        "с вами для подтверждения участия.\n\n"
        "📞 +7 924 416-00-83"
    )

    await state.clear()
    await callback.answer()

@router.callback_query(F.data == "booking_cancel")
async def booking_cancel(
    callback: CallbackQuery,
    state: FSMContext
):
    await state.clear()

    await callback.message.answer(
        "❌ Заявка отменена.\n\n"
        "Если захотите записаться — "
        "откройте раздел «📅 Мероприятия» ещё раз."
    )

    await callback.answer()
