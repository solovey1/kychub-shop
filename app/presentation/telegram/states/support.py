from aiogram.fsm.state import State, StatesGroup


class SupportForm(StatesGroup):
    message = State()


class DisputeForm(StatesGroup):
    reason = State()
