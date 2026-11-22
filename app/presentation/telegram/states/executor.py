from aiogram.fsm.state import State, StatesGroup


class ResultForm(StatesGroup):
    answer = State()


class InfoForm(StatesGroup):
    question = State()


class ReviewForm(StatesGroup):
    comment = State()


class WalletForm(StatesGroup):
    address = State()
