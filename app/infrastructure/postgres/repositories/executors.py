from dataclasses import dataclass

from sqlalchemy import delete, select

from app.application.ports.repositories.executors import ExecutorsGateway
from app.domain.audit import AuditLog
from app.domain.catalog import Service
from app.domain.enums.roles import Role
from app.domain.executor import ExecutorPermission, ExecutorProfile
from app.domain.user import User
from app.infrastructure.postgres.repository_helper import SqlRepositoryHelper
from app.infrastructure.postgres.uow import UoW


@dataclass
class ExecutorsRepository(ExecutorsGateway):
    _uow: UoW
    _helper: SqlRepositoryHelper[ExecutorProfile]

    async def get_profile(self, user_id: int) -> ExecutorProfile | None:
        return await self._helper.get_one(ExecutorProfile.user_id == user_id)

    async def get_by_alias(self, alias: str) -> ExecutorProfile | None:
        return await self._helper.get_one(ExecutorProfile.alias == alias)

    async def add_profile(self, profile: ExecutorProfile) -> None:
        await self._uow.flush(profile)

    async def permission_rows(self, executor_id: int) -> list[tuple[Service, str]]:
        query = (
            select(Service, ExecutorPermission.country_code)
            .join(ExecutorPermission, ExecutorPermission.service_id == Service.id)
            .where(ExecutorPermission.executor_id == executor_id)
            .order_by(Service.id, ExecutorPermission.country_code)
        )
        return [(s, c) for s, c in (await self._helper.session.execute(query)).all()]

    async def replace_permissions(
        self, executor_id: int, service_id: int, country_codes: list[str]
    ) -> None:
        session = self._helper.session
        await session.execute(
            delete(ExecutorPermission).where(
                ExecutorPermission.executor_id == executor_id,
                ExecutorPermission.service_id == service_id,
            )
        )
        session.add_all(
            ExecutorPermission(executor_id=executor_id, service_id=service_id, country_code=c)
            for c in country_codes
        )
        await session.flush()

    async def add_audit(self, record: AuditLog) -> None:
        await self._uow.flush(record)

    async def staff_ids(self) -> list[int]:
        query = select(User.id).where(User.roles.op("&")(int(Role.ADMIN | Role.MANAGER)) != 0)
        return [int(i) for i in await self._helper.session.scalars(query)]
