from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select

from app.application.ports.repositories.orders import OrdersGateway
from app.domain.enums.order import OrderStatus
from app.domain.order import Order, OrderEvent
from app.infrastructure.postgres.repository_helper import SqlRepositoryHelper
from app.infrastructure.postgres.uow import UoW


@dataclass
class OrdersRepository(OrdersGateway):
    _uow: UoW
    _helper: SqlRepositoryHelper[Order]

    async def add(self, order: Order) -> None:
        await self._uow.flush(order)

    async def add_event(self, event: OrderEvent) -> None:
        await self._uow.flush(event)

    async def get_for_user(self, user_id: int, order_id: int) -> Order | None:
        return await self._helper.get_one(Order.id == order_id, Order.user_id == user_id)

    async def list_for_user(self, user_id: int, offset: int, limit: int) -> list[Order]:
        query = (
            select(Order)
            .where(Order.user_id == user_id)
            .order_by(Order.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(await self._helper.session.scalars(query))

    async def count_for_user(self, user_id: int) -> int:
        return await self._helper.count(Order.user_id == user_id)

    async def find_by_token(self, user_id: int, token: str) -> Order | None:
        return await self._helper.get_one(
            Order.user_id == user_id, Order.snapshot.op("->>")("token") == token
        )

    async def get(self, order_id: int) -> Order | None:
        return await self._helper.get_one(Order.id == order_id)

    async def get_for_update(self, order_id: int) -> Order | None:
        query = (
            select(Order)
            .where(Order.id == order_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        order: Order | None = await self._helper.session.scalar(query)
        return order

    async def has_event(self, order_id: int, event_type: str) -> bool:
        query = select(OrderEvent.id).where(
            OrderEvent.order_id == order_id, OrderEvent.type == event_type
        )
        return await self._helper.session.scalar(query.limit(1)) is not None

    async def excluded_executor_ids(self, order_id: int) -> set[int]:
        query = select(OrderEvent.payload.op("->>")("executor_id")).where(
            OrderEvent.order_id == order_id, OrderEvent.type.in_(("refused", "overdue"))
        )
        return {int(v) for v in await self._helper.session.scalars(query) if v is not None}

    async def overdue_ids(self, now: datetime) -> list[int]:
        query = (
            select(Order.id)
            .where(Order.status == OrderStatus.assigned, Order.deadline_at < now)
            .order_by(Order.id)
        )
        return list(await self._helper.session.scalars(query))

    async def stale_ids(self, cutoff: datetime) -> list[int]:
        last_dispatch = (
            select(func.max(OrderEvent.created_at))
            .where(OrderEvent.order_id == Order.id, OrderEvent.type == "dispatch")
            .scalar_subquery()
        )
        query = (
            select(Order.id)
            .where(
                Order.status == OrderStatus.in_queue,
                Order.executor_id.is_(None),
                func.coalesce(last_dispatch, Order.updated_at) < cutoff,
            )
            .order_by(Order.id)
        )
        return list(await self._helper.session.scalars(query))
