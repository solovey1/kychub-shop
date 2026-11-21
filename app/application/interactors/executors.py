import re
from dataclasses import dataclass
from typing import Final

from app.application.errors.shop import (
    AliasTaken,
    ExecutorExists,
    ExecutorNotFound,
    InvalidInput,
    UnknownCountry,
    UnknownService,
)
from app.application.interactors.base import BaseInteractor
from app.application.ports.repositories.catalog import CatalogGateway
from app.application.ports.repositories.executors import ExecutorsGateway
from app.application.ports.repositories.users import UsersGateway
from app.application.ports.uow import UnitOfWork
from app.domain.audit import AuditLog
from app.domain.enums.roles import Role
from app.domain.executor import ExecutorProfile
from app.domain.user import User

_ALIAS_RE: Final = re.compile(r"[\w.\-]{2,32}")


@dataclass(frozen=True)
class CabinetOverview:
    profile: ExecutorProfile
    permissions: dict[str, list[str]]  # service title -> country codes


@dataclass(frozen=True)
class ExecutorAdminInteractor(BaseInteractor):
    uow: UnitOfWork
    users: UsersGateway
    executors: ExecutorsGateway
    catalog: CatalogGateway

    async def register(self, admin_id: int, tg_id: int, alias: str) -> ExecutorProfile:
        alias = alias.strip()
        if not _ALIAS_RE.fullmatch(alias):
            raise InvalidInput("alias")
        try:
            if await self.executors.get_by_alias(alias) is not None:
                raise AliasTaken(alias)
            if await self.executors.get_profile(tg_id) is not None:
                raise ExecutorExists(tg_id)
            user = await self.users.get(tg_id)
            if user is None:  # picked up at the first /start
                user = User(id=tg_id, name="", language="ru")
                await self.users.add(user)
            user.roles |= Role.EXECUTOR
            profile = ExecutorProfile(user_id=tg_id, alias=alias)
            await self.executors.add_profile(profile)
            await self._audit(admin_id, "executor.register", tg_id, {"alias": alias})
            await self.uow.commit()
        except BaseException:
            await self.uow.rollback()
            raise
        return profile

    async def set_permissions(
        self, admin_id: int, tg_id: int, service_code: str, countries: list[str]
    ) -> None:
        """Replaces the permissions for one service. An empty list revokes them."""
        codes = sorted({c.strip().upper() for c in countries if c.strip()})
        try:
            await self._profile(tg_id)
            service = await self.catalog.service_by_code(service_code.strip())
            if service is None:
                raise UnknownService(service_code)
            if codes and len(await self.catalog.countries(codes)) != len(codes):
                raise UnknownCountry(",".join(codes))
            await self.executors.replace_permissions(tg_id, service.id, codes)
            await self._audit(
                admin_id,
                "executor.permissions",
                tg_id,
                {"service": service.code, "countries": codes},
            )
            await self.uow.commit()
        except BaseException:
            await self.uow.rollback()
            raise

    async def set_active(self, admin_id: int, tg_id: int, active: bool) -> None:
        try:
            profile = await self._profile(tg_id)
            profile.is_active = active
            await self._audit(admin_id, "executor.active", tg_id, {"active": active})
            await self.uow.commit()
        except BaseException:
            await self.uow.rollback()
            raise

    async def set_limits(
        self, admin_id: int, tg_id: int, max_parallel: int | None, percent_override: int | None
    ) -> None:
        """`max_parallel=None` keeps the limit; `percent_override=None` clears the override."""
        if max_parallel is not None and not 1 <= max_parallel <= 100:
            raise InvalidInput("max_parallel")
        if percent_override is not None and not 0 <= percent_override <= 100:
            raise InvalidInput("percent")
        try:
            profile = await self._profile(tg_id)
            if max_parallel is not None:
                profile.max_parallel_orders = max_parallel
            profile.percent_override = percent_override
            await self._audit(
                admin_id,
                "executor.limits",
                tg_id,
                {"max_parallel": max_parallel, "percent_override": percent_override},
            )
            await self.uow.commit()
        except BaseException:
            await self.uow.rollback()
            raise

    async def _profile(self, tg_id: int) -> ExecutorProfile:
        profile = await self.executors.get_profile(tg_id)
        if profile is None:
            raise ExecutorNotFound(tg_id)
        return profile

    async def _audit(
        self, admin_id: int, action: str, tg_id: int, payload: dict[str, object]
    ) -> None:
        await self.executors.add_audit(
            AuditLog(actor_id=admin_id, action=action, target=f"user:{tg_id}", payload=payload)
        )


@dataclass(frozen=True)
class ExecutorCabinetInteractor(BaseInteractor):
    executors: ExecutorsGateway

    async def overview(self, user_id: int) -> CabinetOverview | None:
        profile = await self.executors.get_profile(user_id)
        if profile is None:
            return None
        permissions: dict[str, list[str]] = {}
        for service, country in await self.executors.permission_rows(user_id):
            permissions.setdefault(service.title, []).append(country)
        return CabinetOverview(profile, permissions)
