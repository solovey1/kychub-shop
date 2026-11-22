from typing import Any, Final

from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from dishka import FromDishka

from app.presentation.telegram.callbacks.orders import (
    CDCancel,
    CDDeal,
    CDExtAnswer,
    CDOrder,
    CDOrders,
)
from app.presentation.telegram.flows.common.orders import OrdersFlow

router: Final[Router] = Router(name=__name__)


@router.message(Command("orders"))
async def orders_command(_: Message, state: FSMContext, flow: FromDishka[OrdersFlow]) -> Any:
    await state.clear()
    return await flow.list(0)


@router.callback_query(CDOrders.filter())
async def orders(
    _: CallbackQuery, callback_data: CDOrders, state: FSMContext, flow: FromDishka[OrdersFlow]
) -> Any:
    await state.clear()
    return await flow.list(callback_data.page)


@router.callback_query(CDOrder.filter())
async def order(_: CallbackQuery, callback_data: CDOrder, flow: FromDishka[OrdersFlow]) -> Any:
    return await flow.show(callback_data.id, callback_data.page)


@router.callback_query(CDCancel.filter())
async def cancel(_: CallbackQuery, callback_data: CDCancel, flow: FromDishka[OrdersFlow]) -> Any:
    return await flow.cancel(callback_data)


@router.callback_query(CDExtAnswer.filter())
async def extension(
    _: CallbackQuery, callback_data: CDExtAnswer, flow: FromDishka[OrdersFlow]
) -> Any:
    return await flow.answer_extension(callback_data)


@router.callback_query(CDDeal.filter())
async def deal(_: CallbackQuery, callback_data: CDDeal, flow: FromDishka[OrdersFlow]) -> Any:
    return await flow.deal(callback_data)
