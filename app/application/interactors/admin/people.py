from dataclasses import dataclass
from typing import Final

from app.application.errors.shop import Conflict, InvalidField, NotFound
from app.application.interactors.admin.base import AdminInteractor
from app.application.ports.repositories.admin import ExecutorRow
from app.application.ports.repositories.executors import ExecutorsGateway
from app.domain.catalog import Service
from app.domain.enums.roles import Role
from app.domain.executor import ExecutorProfile
from app.domain.order import Order
from app.domain.user import User

SEARCH_LIMIT: Final = 30
USER_ORDERS: Final = 10
# what an admin may switch on a person; ADMIN and OWNER come from the config only
FLAGS: Final = {
    "manager": Role.MANAGER,
    "can_catalog": Role.CAN_CATALOG,
    "can_finance": Role.CAN_FINANCE,
    "can_users": Role.CAN_USERS,
    "can_broadcast": Role.CAN_BROADCAST,
}


@dataclass(frozen=True)
class UserCard:
    user: User
    orders: list[Order]


@dataclass(frozen=True)
class ExecutorDetail:
    profile: ExecutorProfile
    name: str
    permissions: dict[int, list[str]]  # service id -> country codes


@dataclass(frozen=True)
class PeopleAdminInteractor(AdminInteractor):
    executors: ExecutorsGateway

    async def search(self, text: str) -> list[User]:
        if not text.strip():
            return []
        return await self.db.users_search(text, SEARCH_LIMIT)

    async def user(self, user_id: int) -> UserCard:
        user = await self.need(User, user_id, lock=False)
        return UserCard(user, await self.db.orders_of_user(user_id, USER_ORDERS))

    async def set_roles(self, actor: int, user_id: int, changes: dict[str, bool]) -> User:
        """Switches manager and `can_*` flags; admins and owners are not touched."""
        if unknown := set(changes) - set(FLAGS):
            raise InvalidField("roles", f"unknown flag: {sorted(unknown)[0]}")
        async with self.tx():
            user = await self.need(User, user_id)
            if user.roles & (Role.OWNER | Role.ADMIN):
                raise Conflict("protected")
            before = user.roles
            for name, on in changes.items():
                user.roles = user.roles | FLAGS[name] if on else user.roles & ~FLAGS[name]
            if user.roles != before:
                await self.db.audit(
                    actor,
                    "user.roles",
                    f"user:{user_id}",
                    {name: on for name, on in changes.items() if bool(before & FLAGS[name]) != on},
                )
        return user

    async def executor_rows(self) -> list[ExecutorRow]:
        return await self.db.executor_rows()

    async def executor(self, user_id: int) -> ExecutorDetail:
        profile = await self.executors.get_profile(user_id)
        if profile is None:
            raise NotFound(f"executor {user_id}")
        permissions: dict[int, list[str]] = {}
        for service, country in await self.executors.permission_rows(user_id):
            permissions.setdefault(service.id, []).append(country)
        names = await self.db.user_names([user_id])
        return ExecutorDetail(profile, names.get(user_id, ""), permissions)

    async def managers(self) -> list[User]:
        return await self.db.managers()

    async def service_code(self, service_id: int) -> str:
        return (await self.need(Service, service_id, lock=False)).code
