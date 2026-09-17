from aiogram.fsm.state import State, StatesGroup


class BookingState(StatesGroup):
    waiting_name = State()
    waiting_phone = State()