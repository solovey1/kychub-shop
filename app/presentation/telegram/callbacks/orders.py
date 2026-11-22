from aiogram.filters.callback_data import CallbackData


class CDOrders(CallbackData, prefix="ord"):
    page: int = 0


class CDOrder(CallbackData, prefix="ordv"):
    id: int
    page: int = 0


class CDCancel(CallbackData, prefix="oc"):
    id: int
    page: int = 0
    ok: int = 0  # 0 = ask for confirmation, 1 = cancel the order


class CDExtAnswer(CallbackData, prefix="oe"):
    id: int
    rid: int  # the request being answered
    ok: int  # 1 = extend, 0 = no
