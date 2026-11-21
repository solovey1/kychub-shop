from aiogram.fsm.state import State, StatesGroup


class BalanceForm(StatesGroup):
    amount = State()
    promo = State()
