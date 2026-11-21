from dataclasses import dataclass

from sqlalchemy import select

from app.application.ports.repositories.orders import OrdersGateway
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
