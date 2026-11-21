from aiogram.fsm.state import State, StatesGroup


class ResultForm(StatesGroup):
    answer = State()


class ReviewForm(StatesGroup):
    comment = State()
