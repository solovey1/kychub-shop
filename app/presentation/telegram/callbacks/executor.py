from aiogram.filters.callback_data import CallbackData


class CDCabinet(CallbackData, prefix="cab"):
    section: str = ""  # "" = cabinet home


class CDOrderAct(CallbackData, prefix="xo"):
    action: str  # take | accept | refuse | info
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


class CDXCancel(CallbackData, prefix="xc"):
    id: int
    rid: int  # the request being answered
    ok: int  # 1 = agree to cancel, 0 = keep working


class CDExt(CallbackData, prefix="xe"):
    action: str  # ask | pick
    id: int
    value: int = 0  # minutes, for pick
