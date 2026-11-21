from aiogram.filters.callback_data import CallbackData


class CDMenu(CallbackData, prefix="menu"):
    pass


class CDLang(CallbackData, prefix="lang"):
    code: str = ""  # empty = show the language screen
