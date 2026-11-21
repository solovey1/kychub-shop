from aiogram.filters.callback_data import CallbackData


class CDCategory(CallbackData, prefix="cat"):
    id: int = 0  # 0 = catalog root
    page: int = 0


class CDProduct(CallbackData, prefix="prd"):
    id: int


class CDVariant(CallbackData, prefix="var"):
    id: int
