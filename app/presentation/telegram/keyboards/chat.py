from typing import Callable

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.presentation.telegram.callbacks.chat import CDChat
from app.presentation.telegram.callbacks.menu import CDMenu
from app.presentation.telegram.keyboards.common import app_button, button, markup

Tr = Callable[..., str]


def _close(tr: Tr, ticket_id: int) -> list[InlineKeyboardButton]:
    return [button(tr("buttons-chat_close"), CDChat(action="close", id=ticket_id), style="danger")]


def copy_keyboard(
    tr: Tr, conversation_id: int, ticket_id: int | None, *, staff: bool
) -> InlineKeyboardMarkup:
    """Under a copy in the bot: answer here (staff reply to the copy instead, and may close)."""
    reply = button(tr("buttons-chat_reply"), CDChat(action="reply", id=conversation_id))
    rows = [[] if staff else [reply]]
    if staff and ticket_id is not None:
        rows.append(_close(tr, ticket_id))
    return markup(rows)


def ticket_keyboard(
    tr: Tr,
    server_url: str,
    conversation_id: int,
    ticket_id: int,
    *,
    staff: bool,
    close: bool = False,
) -> InlineKeyboardMarkup | None:
    """Under a ticket notice: the chat in the Mini App (and closing, for staff or on request).
    None if empty."""
    path = f"/ticket/{ticket_id}/{conversation_id}" if staff else f"/chat/{conversation_id}"
    opener = app_button(tr("buttons-chat_open"), server_url, path)
    closing = staff or close
    rows = [[opener] if opener else [], _close(tr, ticket_id) if closing else []]
    return markup(rows) if opener or closing else None


def support_keyboard(tr: Tr, order_id: int) -> InlineKeyboardMarkup:
    """The support screen without a ticket: write, or go back to the menu."""
    write = button(
        tr("buttons-support_write"), CDChat(action="write", id=order_id), style="success"
    )
    return markup([[write], [button(tr("buttons-cancel"), CDMenu())]])


def write_keyboard(tr: Tr) -> InlineKeyboardMarkup:
    return markup([[button(tr("buttons-cancel"), CDMenu(), style="danger")]])
