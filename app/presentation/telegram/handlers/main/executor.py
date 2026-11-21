from typing import Any, Final

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from dishka import FromDishka

from app.domain.enums.roles import Role
from app.presentation.telegram.callbacks.executor import CDCabinet, CDOrderAct
from app.presentation.telegram.filters import HasRole
from app.presentation.telegram.flows.executor.cabinet import CabinetFlow
from app.presentation.telegram.flows.executor.orders import ExecutorOrdersFlow

router: Final[Router] = Router(name=__name__)
router.callback_query.filter(HasRole(Role.EXECUTOR))


@router.callback_query(CDCabinet.filter())
async def cabinet(_: CallbackQuery, state: FSMContext, flow: FromDishka[CabinetFlow]) -> Any:
    await state.clear()
    return await flow.show()


@router.callback_query(CDOrderAct.filter())
async def order_action(
    _: CallbackQuery, callback_data: CDOrderAct, flow: FromDishka[ExecutorOrdersFlow]
) -> Any:
    return await flow.action(callback_data)
