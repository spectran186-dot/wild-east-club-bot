from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="📅 Мероприятия"),
            KeyboardButton(text="💰 Цены"),
        ],
        [
            KeyboardButton(text="📞 Контакты"),
            KeyboardButton(text="❓ FAQ"),
        ],
    ],
    resize_keyboard=True,
    input_field_placeholder="Выберите раздел",
)