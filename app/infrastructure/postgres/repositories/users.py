from dataclasses import dataclass
from typing import Optional

from sqlalchemy import select

from app.application.ports.repositories.users import UsersGateway
from app.domain.enums.roles import Role
from app.domain.user import User
from app.infrastructure.postgres.repository_helper import SqlRepositoryHelper
from app.infrastructure.postgres.uow import UoW


@dataclass
class UsersRepository(UsersGateway):
    _uow: UoW
    _helper: SqlRepositoryHelper[User]

    async def get(self, user_id: int) -> Optional[User]:
        return await self._helper.get_one(User.id == user_id)

    async def create(
        self,
        user_id: int,
        name: str,
        language: str,
        language_code: Optional[str],
    ) -> User:
        user: User = User(
            id=user_id,
            name=name,
            language=language,
            language_code=language_code,
        )
        await self._uow.commit(user)
        return user

    async def save(self, user: User) -> None:
        await self._uow.commit(user)

    async def count(self) -> int:
        return await self._helper.count()

    async def staff(self) -> list[User]:
        mask = int(Role.MANAGER | Role.ADMIN)
        query = select(User).where(User.roles.op("&")(mask) != 0).order_by(User.id)
        return list(await self._helper.session.scalars(query))

    async def add(self, user: User) -> None:
        await self._uow.flush(user)
