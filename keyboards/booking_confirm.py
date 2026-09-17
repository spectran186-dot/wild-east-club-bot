from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def booking_confirm_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Подтвердить",
                    callback_data="booking_confirm"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data="booking_cancel"
                )
            ]
        ]
    )