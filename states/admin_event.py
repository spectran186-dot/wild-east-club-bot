from aiogram.fsm.state import State, StatesGroup


class AdminEventState(StatesGroup):
    waiting_date = State()
    waiting_time = State()
    waiting_price = State()
    waiting_meeting_point = State()
    edit_waiting_route = State()
    edit_waiting_date = State()
    edit_waiting_time = State()
    edit_waiting_price = State()
    edit_waiting_meeting_point = State()
    manual_booking_name = State()
    manual_booking_phone = State()
    manual_booking_child = State()
