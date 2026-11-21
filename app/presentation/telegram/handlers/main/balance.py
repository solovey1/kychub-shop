from typing import Any, Final

from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from dishka import FromDishka

from app.domain.enums.roles import Role
from app.presentation.telegram.callbacks.balance import CDBalance, CDCheck, CDPay, CDTopup
from app.presentation.telegram.filters import HasRole
from app.presentation.telegram.flows.common.balance import BalanceFlow
from app.presentation.telegram.states.balance import BalanceForm

router: Final[Router] = Router(name=__name__)


@router.message(Command("balance"))
async def balance_command(_: Message, state: FSMContext, flow: FromDishka[BalanceFlow]) -> Any:
    await state.clear()
    return await flow.show()


@router.message(Command("topup"), HasRole(Role.CAN_FINANCE))
async def admin_topup(
    message: Message, command: CommandObject, flow: FromDishka[BalanceFlow]
) -> Any:
    return await flow.admin_topup(command.args, f"{message.chat.id}:{message.message_id}")


@router.callback_query(CDBalance.filter())
async def balance_action(
    _: CallbackQuery, callback_data: CDBalance, flow: FromDishka[BalanceFlow]
) -> Any:
    return await flow.action(callback_data)


@router.callback_query(CDTopup.filter())
async def topup(
    _: CallbackQuery, callback_data: CDTopup, state: FSMContext, flow: FromDishka[BalanceFlow]
) -> Any:
    await state.clear()
    return await flow.topup(callback_data.amount)


@router.callback_query(CDPay.filter())
async def pay(_: CallbackQuery, callback_data: CDPay, flow: FromDishka[BalanceFlow]) -> Any:
    return await flow.pay(callback_data)


@router.callback_query(CDCheck.filter())
async def check(_: CallbackQuery, callback_data: CDCheck, flow: FromDishka[BalanceFlow]) -> Any:
    return await flow.check(callback_data)


@router.message(BalanceForm.amount, F.text)
async def custom_amount(message: Message, flow: FromDishka[BalanceFlow]) -> Any:
    return await flow.custom_amount(message)


@router.message(BalanceForm.promo, F.text)
async def redeem(message: Message, flow: FromDishka[BalanceFlow]) -> Any:
    return await flow.redeem(message)
