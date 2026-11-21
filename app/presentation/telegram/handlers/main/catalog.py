from typing import Any, Final

from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from dishka import FromDishka

from app.presentation.telegram.callbacks.catalog import CDCategory, CDProduct
from app.presentation.telegram.flows.common.catalog import CatalogFlow

router: Final[Router] = Router(name=__name__)


@router.message(Command("catalog"))
async def catalog_command(_: Message, state: FSMContext, flow: FromDishka[CatalogFlow]) -> Any:
    await state.clear()
    return await flow.category(0, 0)


@router.callback_query(CDCategory.filter())
async def category(
    _: CallbackQuery,
    callback_data: CDCategory,
    state: FSMContext,
    flow: FromDishka[CatalogFlow],
) -> Any:
    await state.clear()
    return await flow.category(callback_data.id, callback_data.page)


@router.callback_query(CDProduct.filter())
async def product(
    _: CallbackQuery,
    callback_data: CDProduct,
    state: FSMContext,
    flow: FromDishka[CatalogFlow],
) -> Any:
    await state.clear()
    return await flow.product(callback_data.id)
