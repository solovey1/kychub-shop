from typing import Any, Final

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from dishka import FromDishka

from app.presentation.telegram.flows.executor.admin import ExecutorAdminFlow

router: Final[Router] = Router(name=__name__)


@router.message(Command("executor_add"))
async def add(_: Message, command: CommandObject, flow: FromDishka[ExecutorAdminFlow]) -> Any:
    return await flow.add(command.args)


@router.message(Command("executor_perm"))
async def perm(_: Message, command: CommandObject, flow: FromDishka[ExecutorAdminFlow]) -> Any:
    return await flow.perm(command.args)


@router.message(Command("executor_off"))
async def off(_: Message, command: CommandObject, flow: FromDishka[ExecutorAdminFlow]) -> Any:
    return await flow.switch(command.args, False)


@router.message(Command("executor_on"))
async def on(_: Message, command: CommandObject, flow: FromDishka[ExecutorAdminFlow]) -> Any:
    return await flow.switch(command.args, True)


@router.message(Command("executor_limits"))
async def limits(_: Message, command: CommandObject, flow: FromDishka[ExecutorAdminFlow]) -> Any:
    return await flow.limits(command.args)
