from aiogram.filters.callback_data import CallbackData


class CDCabinet(CallbackData, prefix="cab"):
    section: str = ""  # "" = cabinet home
