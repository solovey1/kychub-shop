from aiogram.filters.callback_data import CallbackData


class CDChat(CallbackData, prefix="ch"):
    # support: open a ticket (id = order id, 0 = general) | order: write within an order
    # reply: make a conversation current | take | close: a ticket (id = ticket id)
    action: str
    id: int = 0
