from typing import Final

from aiogram import Router
from aiogram.types import Message
from dishka import FromDishka

from app.presentation.telegram.filters.nav import NavTap
from app.presentation.telegram.flows.common.nav import NavFlow

# Included first: a bottom-button tap beats every FSM-state and free-text handler.
router: Final[Router] = Router(name=__name__)


@router.message(NavTap())
async def nav(_: Message, section: str, flow: FromDishka[NavFlow]) -> None:
    await flow.open(section)
