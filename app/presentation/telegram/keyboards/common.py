from typing import Callable, Optional

from aiogram.filters.callback_data import CallbackData
from aiogram.types import DisabledButton, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram_i18n import I18nContext

from app.presentation.telegram.callbacks.menu import CDMenu


def back_keyboard(i18n: I18nContext, data: CallbackData = CDMenu()) -> InlineKeyboardMarkup:
    builder: InlineKeyboardBuilder = InlineKeyboardBuilder()
    builder.button(text=i18n.buttons.back(), callback_data=data)
    return builder.as_markup()


def button(text: str, data: CallbackData, style: Optional[str] = None) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=data.pack(), style=style)


def pager(
    page: int, pages: int, make: Callable[[int], CallbackData]
) -> list[InlineKeyboardButton]:
    """One row: prev / current of total / next. Empty when there is a single page."""
    if pages <= 1:
        return []
    row: list[InlineKeyboardButton] = []
    if page > 0:
        row.append(button("‹", make(page - 1)))
    row.append(InlineKeyboardButton(text=f"{page + 1}/{pages}", disabled=DisabledButton()))
    if page < pages - 1:
        row.append(button("›", make(page + 1)))
    return row


def markup(rows: list[list[InlineKeyboardButton]]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[r for r in rows if r])
