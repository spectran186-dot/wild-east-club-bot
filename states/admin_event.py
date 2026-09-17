from aiogram.fsm.state import State, StatesGroup


class AdminEventState(StatesGroup):
    waiting_date = State()
    waiting_time = State()
    waiting_price = State()
    waiting_meeting_point = State()
