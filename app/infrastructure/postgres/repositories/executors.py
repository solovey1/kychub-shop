from dataclasses import dataclass

from sqlalchemy import delete, exists, func, select, true

from app.application.ports.repositories.executors import Candidate, ExecutorsGateway, StatsRow
from app.domain.audit import AuditLog
from app.domain.catalog import Service
from app.domain.enums.ledger import LedgerAccount
from app.domain.enums.order import OrderStatus
from app.domain.enums.roles import Role
from app.domain.executor import ExecutorPermission, ExecutorProfile
from app.domain.ledger import LedgerEntry, Withdrawal
from app.domain.order import Order, OrderEvent
from app.domain.review import OrderReview
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

    async def aliases(self) -> set[str]:
        return set(await self._helper.session.scalars(select(ExecutorProfile.alias)))

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
        ignore_load: bool = False,
        include_offline: bool = False,
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
                true() if include_offline else ExecutorProfile.is_online,
                exists(permitted.correlate(ExecutorProfile)),
                true() if ignore_load else load < ExecutorProfile.max_parallel_orders,
            )
            .order_by(load, completed.desc(), ExecutorProfile.user_id)
        )
        if exclude:
            query = query.where(ExecutorProfile.user_id.not_in(exclude))
        if only is not None:
            query = query.where(ExecutorProfile.user_id == only)
        rows = (await self._helper.session.execute(query)).all()
        return [Candidate(int(u), int(ld), int(c)) for u, ld, c in rows]

    async def review_exists(self, order_id: int) -> bool:
        return (
            await self._helper.session.scalar(
                select(OrderReview.id).where(OrderReview.order_id == order_id)
            )
            is not None
        )

    async def add_review(self, review: OrderReview) -> None:
        await self._uow.flush(review)

    async def stats(self, executor_id: int) -> StatsRow:
        session = self._helper.session
        mine = Order.executor_id == executor_id

        async def orders_in(*statuses: OrderStatus) -> int:
            query = select(func.count()).select_from(Order).where(mine, Order.status.in_(statuses))
            return int(await session.scalar(query) or 0)

        async def events(kind: str) -> int:
            query = select(func.count()).where(
                OrderEvent.type == kind,
                OrderEvent.payload.op("->>")("executor_id") == str(executor_id),
            )
            return int(await session.scalar(query) or 0)

        async def failed() -> int:
            """Failed and refunded orders; a cancellation the executor agreed to is no fault."""
            agreed = exists().where(
                OrderEvent.order_id == Order.id, OrderEvent.type == "cancel_agreed"
            )
            query = (
                select(func.count())
                .select_from(Order)
                .where(mine, Order.status.in_((OrderStatus.failed, OrderStatus.refunded)), ~agreed)
            )
            return int(await session.scalar(query) or 0)

        seconds = func.extract("epoch", Order.completed_at - Order.assigned_at)
        minutes = await session.scalar(
            select(func.avg(seconds)).where(
                mine,
                Order.status == OrderStatus.completed,
                Order.assigned_at.is_not(None),
                Order.completed_at.is_not(None),
            )
        )
        score = await session.scalar(
            select(func.avg(OrderReview.score)).where(OrderReview.executor_id == executor_id)
        )
        return StatsRow(
            completed=await orders_in(OrderStatus.completed),
            failed=await failed(),
            overdue=await events("overdue"),
            refused=await events("refused"),
            avg_minutes=None if minutes is None else float(minutes) / 60,
            avg_score=None if score is None else float(score),
        )

    async def add_withdrawal(self, withdrawal: Withdrawal) -> None:
        await self._uow.flush(withdrawal)

    async def wallet_entries(self, user_id: int, limit: int) -> list[LedgerEntry]:
        query = (
            select(LedgerEntry)
            .where(
                LedgerEntry.user_id == user_id,
                LedgerEntry.account.in_(
                    (LedgerAccount.executor_hold, LedgerAccount.executor_available)
                ),
            )
            .order_by(LedgerEntry.id.desc())
            .limit(limit)
        )
        return list(await self._helper.session.scalars(query))
