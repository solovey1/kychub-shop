from aiogram.filters.callback_data import CallbackData


class CDOrders(CallbackData, prefix="ord"):
    page: int = 0


class CDOrder(CallbackData, prefix="ordv"):
    id: int
    page: int = 0
