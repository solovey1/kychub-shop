from aiogram.filters.callback_data import CallbackData


class CDCabinet(CallbackData, prefix="cab"):
    section: str = ""  # "" = cabinet home


class CDOrderAct(CallbackData, prefix="xo"):
    action: str  # take | refuse
    id: int
