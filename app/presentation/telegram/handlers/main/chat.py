from typing import Any, Final

from aiogram import Router
from aiogram.types import CallbackQuery
from dishka import FromDishka

from app.presentation.telegram.callbacks.chat import CDChat
from app.presentation.telegram.flows.common.chat import ChatFlow

router: Final[Router] = Router(name=__name__)


@router.callback_query(CDChat.filter())
async def chat(_: CallbackQuery, callback_data: CDChat, flow: FromDishka[ChatFlow]) -> Any:
    return await flow.action(callback_data)
