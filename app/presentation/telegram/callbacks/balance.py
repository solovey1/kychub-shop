from aiogram.filters.callback_data import CallbackData


class CDBalance(CallbackData, prefix="bal"):
    action: str = ""  # "" = balance screen | topup | custom | promo


class CDTopup(CallbackData, prefix="top"):
    amount: int  # whole dollars from the quick buttons


class CDPay(CallbackData, prefix="pay"):
    provider: str
    cents: int


class CDCheck(CallbackData, prefix="chk"):
    id: int
