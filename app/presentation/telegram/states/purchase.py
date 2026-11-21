from aiogram.fsm.state import State, StatesGroup


class PurchaseForm(StatesGroup):
    answer = State()
    promo = State()
