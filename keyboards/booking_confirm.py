from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def booking_confirm_keyboard(child_added=False):
    child_text = "👶 Ребенок добавлен +500 ₽" if child_added else "👶 Ребенок с вами на сапе +500 ₽"

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=child_text, callback_data="booking_child")],
            [InlineKeyboardButton(text="💬 Добавить комментарий", callback_data="booking_comment")],
            [InlineKeyboardButton(text="👤 Добавить еще участника сплава", callback_data="booking_add_participant")],
            [InlineKeyboardButton(text="✅ Подтвердить", callback_data="booking_confirm")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="booking_cancel")],
        ]
    )
