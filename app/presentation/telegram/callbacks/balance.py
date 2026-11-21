from aiogram.filters.callback_data import CallbackData


class CDBalance(CallbackData, prefix="bal"):
    action: str = ""  # "" = balance screen | topup | custom | promo


class CDTopup(CallbackData, prefix="top"):
    amount: int
