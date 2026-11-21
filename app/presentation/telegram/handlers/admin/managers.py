from typing import Any, Final

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from dishka import FromDishka

from app.presentation.telegram.flows.common.managers import ManagerAdminFlow

router: Final[Router] = Router(name=__name__)


@router.message(Command("manager_add"))
async def add(_: Message, command: CommandObject, flow: FromDishka[ManagerAdminFlow]) -> Any:
    return await flow.run(command.args, add=True)


@router.message(Command("manager_del"))
async def delete(_: Message, command: CommandObject, flow: FromDishka[ManagerAdminFlow]) -> Any:
    return await flow.run(command.args, add=False)
