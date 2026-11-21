from dataclasses import dataclass

from app.application.errors.shop import ManagerExists, ManagerNotFound
from app.application.interactors.base import BaseInteractor
from app.application.ports.repositories.executors import ExecutorsGateway
from app.application.ports.repositories.users import UsersGateway
from app.application.ports.uow import UnitOfWork
from app.domain.audit import AuditLog
from app.domain.enums.roles import Role
from app.domain.user import User


@dataclass(frozen=True)
class ManagerAdminInteractor(BaseInteractor):
    uow: UnitOfWork
    users: UsersGateway
    executors: ExecutorsGateway  # only for the audit log

    async def add(self, admin_id: int, tg_id: int) -> None:
        try:
            user = await self.users.get(tg_id)
            if user is None:  # picked up at the first /start
                user = User(id=tg_id, name="", language="ru")
                await self.users.add(user)
            if user.roles & Role.MANAGER:
                raise ManagerExists(tg_id)
            user.roles |= Role.MANAGER
            await self._audit(admin_id, "manager.add", tg_id)
            await self.uow.commit()
        except BaseException:
            await self.uow.rollback()
            raise

    async def remove(self, admin_id: int, tg_id: int) -> None:
        try:
            user = await self.users.get(tg_id)
            if user is None or not user.roles & Role.MANAGER:
                raise ManagerNotFound(tg_id)
            user.roles &= ~Role.MANAGER
            await self._audit(admin_id, "manager.remove", tg_id)
            await self.uow.commit()
        except BaseException:
            await self.uow.rollback()
            raise

    async def _audit(self, admin_id: int, action: str, tg_id: int) -> None:
        await self.executors.add_audit(
            AuditLog(actor_id=admin_id, action=action, target=f"user:{tg_id}", payload={})
        )
