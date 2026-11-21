from typing import Any, Final

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from dishka import FromDishka

from app.presentation.telegram.callbacks.feedback import CDRate, CDTip
from app.presentation.telegram.flows.common.feedback import FeedbackFlow
from app.presentation.telegram.states.feedback import TipForm

router: Final[Router] = Router(name=__name__)


@router.callback_query(CDRate.filter())
async def rate(_: CallbackQuery, callback_data: CDRate, flow: FromDishka[FeedbackFlow]) -> Any:
    return await flow.rate(callback_data)


@router.callback_query(CDTip.filter())
async def tip(_: CallbackQuery, callback_data: CDTip, flow: FromDishka[FeedbackFlow]) -> Any:
    return await flow.tip(callback_data)


@router.message(TipForm.amount, F.text)
async def custom_amount(message: Message, flow: FromDishka[FeedbackFlow]) -> Any:
    return await flow.custom_amount(message)
