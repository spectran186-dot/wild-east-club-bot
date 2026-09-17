from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


main_menu = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="📅 Мероприятия", callback_data="menu_events"),
            InlineKeyboardButton(text="💰 Цены", callback_data="menu_prices"),
        ],
        [
            InlineKeyboardButton(text="📞 Контакты", callback_data="menu_contacts"),
            InlineKeyboardButton(text="❓ FAQ", callback_data="menu_faq"),
        ],
    ]
)


def back_to_menu_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Главное меню", callback_data="menu_back")]
        ]
    )
