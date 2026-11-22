from typing import Any, Final

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from dishka import FromDishka

from app.presentation.telegram.callbacks.chat import CDChat
from app.presentation.telegram.flows.common.chat import ChatFlow
from app.presentation.telegram.states.support import SupportForm

router: Final[Router] = Router(name=__name__)


@router.callback_query(CDChat.filter())
async def chat(_: CallbackQuery, callback_data: CDChat, flow: FromDishka[ChatFlow]) -> Any:
    return await flow.action(callback_data)


@router.message(SupportForm.message, ~F.text.startswith("/"))
async def first_message(message: Message, flow: FromDishka[ChatFlow]) -> Any:
    return await flow.first_message(message)
