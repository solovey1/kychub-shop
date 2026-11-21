from typing import Any, Final

from aiogram import Router
from aiogram.enums import ChatType
from aiogram.types import Message
from dishka import FromDishka

from app.presentation.telegram.filters.states import NoneState
from app.presentation.telegram.flows.common.relay import RelayFlow

# The last router of the chain: it sees only what nothing else took, and never while an FSM
# form (purchase questions, result submission, ...) is waiting for the user.
router: Final[Router] = Router(name=__name__)
router.message.filter(NoneState)


def _is_free_text(message: Message) -> bool:
    return (
        message.chat.type == ChatType.PRIVATE
        and message.via_bot is None
        and not (message.text or "").startswith("/")
    )


@router.message(_is_free_text)
async def relay(message: Message, flow: FromDishka[RelayFlow]) -> Any:
    return await flow.route(message)
