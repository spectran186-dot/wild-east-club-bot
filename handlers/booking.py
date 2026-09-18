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

_event_cache = {}
_pending_confirmations = set()


def cache_event(event):
    _event_cache[event[0]] = event


def booking_keyboard(event_id):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Записаться", callback_data=f"book_{event_id}")]
        ]
    )


def event_text(event):
    (
        _event_id, _route_id, event_date, event_time, price,
        route_title, start_point, finish_point, meeting_point,
    ) = event

    return (
        "🌊 <b>Вы выбрали мероприятие</b>\n\n"
        f"🛶 <b>{route_title}</b>\n"
        f"📅 {event_date[8:10]}.{event_date[5:7]}.{event_date[:4]}\n"
        f"🕐 {event_time}\n"
        f"📍 {meeting_point or start_point}\n"
        f"💰 <b>{price} ₽</b>\n\n"
        "👤 Теперь введите ваше имя:"
    )


@router.callback_query(F.data.startswith("book_"))
async def booking(callback: CallbackQuery, state: FSMContext):
    await callback.answer()

    event_id = int(callback.data.split("_", 1)[1])

    event = _event_cache.get(event_id)

    if event is None:
        event_info = await db.get_event_info(event_id)
        if event_info:
            event = (
                event_info[0], None, event_info[1], event_info[2], event_info[3],
                event_info[4], event_info[5], event_info[6], event_info[7],
            )
            cache_event(event)

    if not event:
        await callback.message.answer(
            "⚠️ Это мероприятие больше недоступно.\n\n"
            "Откройте раздел «Мероприятия» и выберите другое."
        )
        return

    await state.update_data(event_id=event_id)
    await state.set_state(BookingState.waiting_name)
    await callback.message.answer(
        "👤 <b>Введите имя участника:</b>\n\n"
        "Можно указать имя и фамилию.",
        parse_mode="HTML",
    )


@router.message(BookingState.waiting_name)
async def get_name(message: Message, state: FSMContext):
    full_name = (message.text or "").strip()

    if not full_name:
        await message.answer("Пожалуйста, введите ваше имя.")
        return

    await state.update_data(full_name=full_name)
    await state.set_state(BookingState.waiting_phone)

    await message.answer(
        "📞 Отправьте номер телефона кнопкой ниже "
        "или введите его вручную в формате 7XXXXXXXXX:",
        reply_markup=phone_keyboard(),
    )


@router.message(BookingState.waiting_phone)
async def get_phone(message: Message, state: FSMContext):
    phone = message.contact.phone_number if message.contact else (message.text or "").strip()

    if not phone:
        await message.answer("Пожалуйста, отправьте номер телефона или введите его вручную.")
        return

    await state.update_data(phone=phone, child_added=False, comment="")
    await show_booking_review(message, state)


def format_booking_review(data, event):
    participants = list(data.get("participants", []))
    current = {
        "full_name": data.get("full_name"),
        "phone": data.get("phone"),
        "children": 1 if data.get("child_added") else 0,
        "comment": data.get("comment", ""),
    }
    participants.append(current)

    if event:
        (
            _event_id, _route_id, event_date, event_time, price,
            route_title, start_point, finish_point, meeting_point,
        ) = event
        event_info = (
            f"🛶 Маршрут: {route_title}\n"
            f"📅 Дата: {event_date[8:10]}.{event_date[5:7]}.{event_date[:4]}\n"
            f"🕐 Время: {event_time}\n"
            f"📍 {meeting_point or start_point}\n"
            f"💰 Стоимость: {price} ₽\n\n"
        )
    else:
        event_info = ""

    lines = ["📋 <b>Проверьте данные заявки</b>", "", event_info.rstrip()]
    total = 0

    for index, participant in enumerate(participants, 1):
        child_extra = 500 if participant.get("children") else 0
        total += (event[4] if event else 0) + child_extra
        lines.extend([
            f"👤 <b>Участник {index}</b>",
            f"Имя: {participant.get('full_name')}",
            f"Телефон: {participant.get('phone')}",
        ])
        if participant.get("children"):
            lines.append("👶 Ребенок с вами на SUP: +500 ₽")
        if participant.get("comment"):
            lines.append(f"💬 Комментарий: {participant['comment']}")
        lines.append("")

    if event:
        lines.append(f"💰 <b>Итого: {total} ₽</b>")
    lines.extend(["", "Всё верно?"])
    return "\n".join(lines)


async def show_booking_review(message: Message, state: FSMContext):
    data = await state.get_data()
    event = _event_cache.get(data.get("event_id"))
    await message.answer(
        format_booking_review(data, event),
        reply_markup=booking_confirm_keyboard(bool(data.get("child_added"))),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "booking_child")
async def booking_child(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if data.get("child_added"):
        await callback.answer("Ребенок уже добавлен", show_alert=True)
        return
    await callback.answer()
    await state.update_data(child_added=True)
    await show_booking_review(callback.message, state)


@router.callback_query(F.data == "booking_comment")
async def booking_comment(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(BookingState.waiting_comment)
    await callback.message.answer(
        "💬 <b>Введите комментарий к заявке:</b>\\n\\n"
        "Например: пожелания, особенности участия или другая важная информация.",
        parse_mode="HTML",
    )


@router.message(BookingState.waiting_comment)
async def get_booking_comment(message: Message, state: FSMContext):
    comment = (message.text or "").strip()
    if not comment:
        await message.answer("Пожалуйста, введите комментарий текстом.")
        return
    await state.update_data(comment=comment)
    await state.set_state(BookingState.waiting_phone)
    await show_booking_review(message, state)


@router.callback_query(F.data == "booking_add_participant")
async def booking_add_participant(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    if not data.get("full_name") or not data.get("phone"):
        await callback.message.answer("❌ Сначала заполните данные текущего участника.")
        return

    participants = list(data.get("participants", []))
    participants.append({
        "full_name": data["full_name"],
        "phone": data["phone"],
        "children": 1 if data.get("child_added") else 0,
        "comment": data.get("comment", ""),
    })

    await state.update_data(
        participants=participants,
        full_name=None,
        phone=None,
        child_added=False,
        comment="",
    )
    await state.set_state(BookingState.waiting_name)
    await callback.message.answer(
        "👤 <b>Введите имя следующего участника:</b>\\n\\n"
        "Можно указать имя и фамилию.",
        parse_mode="HTML",
    )


@router.callback_query(F.data == "booking_confirm")
async def booking_confirm(callback: CallbackQuery, state: FSMContext):
    await callback.answer()

    data = await state.get_data()
    event_id = data.get("event_id")
    user_id = callback.from_user.id
    participants = list(data.get("participants", []))

    if data.get("full_name") and data.get("phone"):
        participants.append({
            "full_name": data["full_name"],
            "phone": data["phone"],
            "children": 1 if data.get("child_added") else 0,
            "comment": data.get("comment", ""),
        })

    if not event_id or not participants:
        await callback.message.answer(
            "❌ Не удалось получить данные заявки.\\n"
            "Пожалуйста, начните запись заново."
        )
        await state.clear()
        return

    lock_key = (user_id, event_id)

    for participant in participants:
        if await db.has_booking(event_id, participant["full_name"], participant["phone"]):
            await callback.message.edit_text(
                "ℹ️ <b>Такая заявка уже существует.</b>\\n\\n"
                f"👤 Имя: {participant['full_name']}\\n"
                f"📞 Телефон: {participant['phone']}\\n\\n"
                "Для этого мероприятия заявка с такими данными уже была создана.",
                parse_mode="HTML",
            )
            return

    if lock_key in _pending_confirmations:
        await callback.message.edit_text(
            "⏳ Заявка уже отправляется.\\n\\nПожалуйста, подождите несколько секунд."
        )
        return

    _pending_confirmations.add(lock_key)
    await callback.message.edit_text(
        "⏳ Заявка отправляется...\\n\\nПожалуйста, подождите несколько секунд."
    )

    try:
        # Повторная проверка непосредственно перед записью.
        for participant in participants:
            if await db.has_booking(event_id, participant["full_name"], participant["phone"]):
                await callback.message.edit_text(
                    "ℹ️ <b>Одна из заявок уже существует.</b>\\n\\n"
                    "Повторная заявка не создана.",
                    parse_mode="HTML",
                )
                return

        event = _event_cache.get(event_id)
        base_price = event[4] if event else 0

        for participant in participants:
            await db.add_booking(
                telegram_id=user_id,
                event_id=event_id,
                full_name=participant["full_name"],
                phone=participant["phone"],
                children=participant["children"],
                comment=participant["comment"],
            )

        if event:
            (
                _event_id, _route_id, event_date, event_time, price,
                route_title, _start_point, _finish_point, _meeting_point,
            ) = event

            try:
                notification_lines = [
                    "🔔 НОВЫЕ ЗАЯВКИ!\\n",
                    f"📅 Дата: {event_date}",
                    f"🕐 Время: {event_time}",
                    f"🛶 Маршрут: {route_title}",
                    "",
                ]
                total = 0
                for index, participant in enumerate(participants, 1):
                    child_extra = 500 if participant["children"] else 0
                    total += base_price + child_extra
                    notification_lines.extend([
                        f"👤 Участник {index}: {participant['full_name']}",
                        f"📞 Телефон: {participant['phone']}",
                    ])
                    if participant["children"]:
                        notification_lines.append("👶 Ребенок с вами на SUP: +500 ₽")
                    if participant["comment"]:
                        notification_lines.append(f"💬 Комментарий: {participant['comment']}")
                    notification_lines.append("")

                notification_lines.append(f"💰 Итого: {total} ₽")
                await callback.bot.send_message(ADMIN_ID, "\\n".join(notification_lines))
            except Exception:
                pass

        total = sum(base_price + (500 if p["children"] else 0) for p in participants)
        await callback.message.edit_text(
            "🎉 <b>Заявка принята!</b>\\n\\n"
            f"Участников: {len(participants)}\\n"
            f"💰 Итого: {total} ₽\\n\\n"
            "Мы приняли вашу заявку на САП-сплав с командой Wild East Club.\\n\\n"
            "В ближайшее время организатор свяжется с вами для подтверждения участия.\\n\\n"
            "📞 +7 924 416-00-83",
            parse_mode="HTML",
        )
    except Exception:
        await callback.message.edit_text(
            "⚠️ Не удалось отправить заявку.\\n\\n"
            "Попробуйте ещё раз через несколько секунд."
        )
        raise
    finally:
        _pending_confirmations.discard(lock_key)
        await state.clear()


@router.callback_query(F.data == "booking_cancel")
async def booking_cancel(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await callback.message.edit_text(
        "❌ Заявка отменена.\n\n"
        "Если захотите записаться — откройте раздел «Мероприятия» ещё раз."
    )
