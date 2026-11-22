from typing import Any, Final

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from dishka import FromDishka

from app.domain.enums.roles import Role
from app.presentation.telegram.callbacks.executor import (
    CDCabinet,
    CDExt,
    CDOrderAct,
    CDReview,
    CDXCancel,
    CDXOrder,
    CDXOrders,
    CDXResult,
)
from app.presentation.telegram.filters import HasRole
from app.presentation.telegram.flows.executor.cabinet import CabinetFlow
from app.presentation.telegram.flows.executor.orders import ExecutorOrdersFlow
from app.presentation.telegram.flows.executor.review import ReviewFlow
from app.presentation.telegram.states.executor import InfoForm, ResultForm, ReviewForm, WalletForm

router: Final[Router] = Router(name=__name__)
router.callback_query.filter(HasRole(Role.EXECUTOR))
router.message.filter(HasRole(Role.EXECUTOR))

# admins and managers check the finished work; one filter for the whole router
review_router: Final[Router] = Router(name=f"{__name__}.review")
review_router.callback_query.filter(HasRole(Role.ADMIN | Role.MANAGER))
review_router.message.filter(HasRole(Role.ADMIN | Role.MANAGER))


@router.callback_query(CDCabinet.filter())
async def cabinet(
    _: CallbackQuery, callback_data: CDCabinet, flow: FromDishka[CabinetFlow]
) -> Any:
    return await flow.section(callback_data)


@router.callback_query(CDOrderAct.filter())
async def order_action(
    _: CallbackQuery, callback_data: CDOrderAct, flow: FromDishka[ExecutorOrdersFlow]
) -> Any:
    return await flow.action(callback_data)


@router.callback_query(CDExt.filter())
async def extension(
    _: CallbackQuery, callback_data: CDExt, flow: FromDishka[ExecutorOrdersFlow]
) -> Any:
    return await flow.extension(callback_data)


@router.callback_query(CDXCancel.filter())
async def cancel_answer(
    _: CallbackQuery, callback_data: CDXCancel, flow: FromDishka[ExecutorOrdersFlow]
) -> Any:
    return await flow.cancel_answer(callback_data)


@router.callback_query(CDXOrders.filter())
async def orders(
    _: CallbackQuery, callback_data: CDXOrders, flow: FromDishka[ExecutorOrdersFlow]
) -> Any:
    return await flow.list(callback_data.page)


@router.callback_query(CDXOrder.filter())
async def order(
    _: CallbackQuery, callback_data: CDXOrder, flow: FromDishka[ExecutorOrdersFlow]
) -> Any:
    return await flow.show(callback_data.id, callback_data.page)


@router.callback_query(CDXResult.filter())
async def result_action(
    _: CallbackQuery, callback_data: CDXResult, flow: FromDishka[ExecutorOrdersFlow]
) -> Any:
    return await flow.result_action(callback_data)


@router.message(ResultForm.answer, F.text | F.document | F.photo)
async def result_answer(message: Message, flow: FromDishka[ExecutorOrdersFlow]) -> Any:
    return await flow.answer_message(message)


@router.message(InfoForm.question, F.text)
async def info_question(message: Message, flow: FromDishka[ExecutorOrdersFlow]) -> Any:
    return await flow.info_question(message)


@router.message(WalletForm.address, F.text)
async def wallet_address(message: Message, flow: FromDishka[CabinetFlow]) -> Any:
    return await flow.set_wallet(message)


@review_router.callback_query(CDReview.filter())
async def review_action(
    _: CallbackQuery, callback_data: CDReview, flow: FromDishka[ReviewFlow]
) -> Any:
    return await flow.action(callback_data)


@review_router.message(ReviewForm.comment, F.text)
async def review_comment(message: Message, flow: FromDishka[ReviewFlow]) -> Any:
    return await flow.send_back(message)
