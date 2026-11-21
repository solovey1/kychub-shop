from typing import Optional

from aiogram.enums import ChatType
from aiogram.filters import Filter
from aiogram.types import Chat, TelegramObject
from dishka import AsyncContainer

from app.domain.enums.roles import Role
from app.domain.user import User


class HasRole(Filter):
    """Passes only in a private chat, so admin output never lands in a group."""

    def __init__(self, role: Role) -> None:
        self.role = role

    async def __call__(
        self,
        event: TelegramObject,
        dishka_container: AsyncContainer,
        event_chat: Optional[Chat] = None,
    ) -> bool:
        if event_chat is None or event_chat.type != ChatType.PRIVATE:
            return False
        user = await dishka_container.get(User)
        return bool(user.roles & self.role)
