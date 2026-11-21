from aiogram.filters.callback_data import CallbackData


class CDRate(CallbackData, prefix="rt"):
    id: int
    score: int = 0  # 0 = show the rating screen


class CDTip(CallbackData, prefix="tp"):
    id: int
    c: int = 0  # cents: >0 tip now, 0 = show the amounts, -1 = ask for an amount
    t: str = ""  # idempotency token of the screen the amount was chosen on
