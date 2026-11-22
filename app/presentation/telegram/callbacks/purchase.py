from aiogram.filters.callback_data import CallbackData


class CDPurchase(CallbackData, prefix="pur"):
    action: str  # pay | promo | cancel | choice | skip | prev | done
    value: int = 0
