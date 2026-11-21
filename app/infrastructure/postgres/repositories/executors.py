from dataclasses import dataclass

from sqlalchemy import delete, exists, func, select

from app.application.ports.repositories.executors import Candidate, ExecutorsGateway
from app.domain.audit import AuditLog
from app.domain.catalog import Service
from app.domain.enums.order import OrderStatus
from app.domain.enums.roles import Role
from app.domain.executor import ExecutorPermission, ExecutorProfile
from app.domain.order import Order
from app.domain.user import User
from app.infrastructure.postgres.repository_helper import SqlRepositoryHelper
from app.infrastructure.postgres.uow import UoW


@dataclass
class ExecutorsRepository(ExecutorsGateway):
    _uow: UoW
    _helper: SqlRepositoryHelper[ExecutorProfile]

    async def get_profile(self, user_id: int) -> ExecutorProfile | None:
        return await self._helper.get_one(ExecutorProfile.user_id == user_id)

    async def get_profile_for_update(self, user_id: int) -> ExecutorProfile | None:
        query = (
            select(ExecutorProfile)
            .where(ExecutorProfile.user_id == user_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        profile: ExecutorProfile | None = await self._helper.session.scalar(query)
        return profile

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

    async def candidates(
        self,
        service_id: int,
        country_code: str | None,
        exclude: set[int],
        only: int | None = None,
    ) -> list[Candidate]:
        mine = Order.executor_id == ExecutorProfile.user_id
        load = (
            select(func.count())
            .where(mine, Order.status.in_((OrderStatus.assigned, OrderStatus.ready)))
            .correlate(ExecutorProfile)
            .scalar_subquery()
        )
        completed = (
            select(func.count())
            .where(mine, Order.status == OrderStatus.completed)
            .correlate(ExecutorProfile)
            .scalar_subquery()
        )
        permitted = select(ExecutorPermission.executor_id).where(
            ExecutorPermission.executor_id == ExecutorProfile.user_id,
            ExecutorPermission.service_id == service_id,
        )
        if country_code is not None:
            permitted = permitted.where(ExecutorPermission.country_code == country_code)
        query = (
            select(ExecutorProfile.user_id, load, completed)
            .where(
                ExecutorProfile.is_active,
                exists(permitted.correlate(ExecutorProfile)),
                load < ExecutorProfile.max_parallel_orders,
            )
            .order_by(load, completed.desc(), ExecutorProfile.user_id)
        )
        if exclude:
            query = query.where(ExecutorProfile.user_id.not_in(exclude))
        if only is not None:
            query = query.where(ExecutorProfile.user_id == only)
        rows = (await self._helper.session.execute(query)).all()
        return [Candidate(int(u), int(ld), int(c)) for u, ld, c in rows]
