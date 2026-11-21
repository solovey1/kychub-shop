from typing import Final

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from dishka import FromDishka

from app.presentation.telegram.callbacks.catalog import CDVariant
from app.presentation.telegram.callbacks.purchase import CDPurchase
from app.presentation.telegram.flows.common.purchase import PurchaseFlow
from app.presentation.telegram.states.purchase import PurchaseForm

router: Final[Router] = Router(name=__name__)


@router.callback_query(CDVariant.filter())
async def start(
    _: CallbackQuery, callback_data: CDVariant, flow: FromDishka[PurchaseFlow]
) -> None:
    await flow.start(callback_data.id)


@router.callback_query(CDPurchase.filter())
async def action(
    _: CallbackQuery, callback_data: CDPurchase, flow: FromDishka[PurchaseFlow]
) -> None:
    await flow.action(callback_data)


@router.message(PurchaseForm.answer, F.text | F.document | F.photo)
async def answer(message: Message, flow: FromDishka[PurchaseFlow]) -> None:
    await flow.answer_message(message)


@router.message(PurchaseForm.promo, F.text)
async def promo(message: Message, flow: FromDishka[PurchaseFlow]) -> None:
    await flow.apply_promo(message)
