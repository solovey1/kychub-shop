from aiogram.filters import Filter
from aiogram.types import TelegramObject
from dishka import AsyncContainer

from app.domain.enums.roles import Role
from app.domain.user import User


class HasRole(Filter):
    def __init__(self, role: Role) -> None:
        self.role = role

    async def __call__(self, event: TelegramObject, dishka_container: AsyncContainer) -> bool:
        user = await dishka_container.get(User)
        return bool(user.roles & self.role)
