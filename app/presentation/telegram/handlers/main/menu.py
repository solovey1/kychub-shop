from typing import Any, Final

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from dishka import FromDishka

from app.presentation.telegram.callbacks.menu import CDLang, CDMenu
from app.presentation.telegram.flows.common.menu import CommonMenuFlow

router: Final[Router] = Router(name=__name__)


@router.message(CommandStart())
async def start(_: Message, state: FSMContext, flow: FromDishka[CommonMenuFlow]) -> Any:
    await state.clear()
    return await flow.start()


@router.callback_query(CDMenu.filter())
async def menu(_: CallbackQuery, state: FSMContext, flow: FromDishka[CommonMenuFlow]) -> Any:
    await state.clear()
    return await flow.greeting()


@router.callback_query(CDLang.filter())
async def language(
    _: CallbackQuery, callback_data: CDLang, state: FSMContext, flow: FromDishka[CommonMenuFlow]
) -> Any:
    await state.clear()
    if not callback_data.code:
        return await flow.language()
    return await flow.set_language(callback_data.code)
