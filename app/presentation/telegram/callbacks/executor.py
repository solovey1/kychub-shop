from aiogram.filters.callback_data import CallbackData


class CDCabinet(CallbackData, prefix="cab"):
    section: str = ""  # "" = cabinet home


class CDOrderAct(CallbackData, prefix="xo"):
    action: str  # take | refuse
    id: int


class CDXOrders(CallbackData, prefix="xl"):
    page: int = 0


class CDXOrder(CallbackData, prefix="xv"):
    id: int
    page: int = 0


class CDXResult(CallbackData, prefix="xr"):
    action: str  # start | choice | skip | cancel | done
    id: int
    value: int = 0


class CDReview(CallbackData, prefix="rv"):
    action: str  # open | ok | back | fail | failok
    id: int


class CDExt(CallbackData, prefix="xe"):
    action: str  # ask | pick
    id: int
    value: int = 0  # minutes, for pick
