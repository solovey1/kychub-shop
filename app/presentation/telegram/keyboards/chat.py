from typing import Callable

from aiogram.types import InlineKeyboardMarkup

from app.presentation.telegram.callbacks.chat import CDChat
from app.presentation.telegram.keyboards.common import button, markup

Tr = Callable[..., str]


def copy_keyboard(
    tr: Tr, conversation_id: int, ticket_id: int | None, *, staff: bool
) -> InlineKeyboardMarkup:
    """Under a delivered copy: answer here; managers also get the history and closing."""
    rows = [[button(tr("buttons-chat_reply"), CDChat(action="reply", id=conversation_id))]]
    if staff and ticket_id is not None:
        rows.append(
            [
                button(tr("buttons-chat_history"), CDChat(action="history", id=conversation_id)),
                button(
                    tr("buttons-chat_close"),
                    CDChat(action="close", id=ticket_id),
                    style="danger",
                ),
            ]
        )
    return markup(rows)
