from aiogram.fsm.state import State, StatesGroup


class TipForm(StatesGroup):
    amount = State()
