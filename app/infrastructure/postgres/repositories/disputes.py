from collections.abc import Collection
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select

from app.application.ports.repositories.disputes import DisputesGateway
from app.domain.dispute import Dispute
from app.domain.order import Order
from app.infrastructure.postgres.repository_helper import SqlRepositoryHelper
from app.infrastructure.postgres.uow import UoW


@dataclass
class DisputesRepository(DisputesGateway):
    _uow: UoW
    _helper: SqlRepositoryHelper[Dispute]

    async def add(self, dispute: Dispute) -> None:
        await self._uow.flush(dispute)

    async def open_for_order(self, order_id: int) -> Dispute | None:
        query = (
            select(Dispute)
            .where(Dispute.order_id == order_id, Dispute.resolved_at.is_(None))
            .execution_options(populate_existing=True)
        )
        dispute: Dispute | None = await self._helper.session.scalar(query)
        return dispute

    async def open_for_orders(self, order_ids: Collection[int]) -> dict[int, Dispute]:
        if not order_ids:
            return {}
        query = select(Dispute).where(
            Dispute.order_id.in_(order_ids), Dispute.resolved_at.is_(None)
        )
        return {d.order_id: d for d in await self._helper.session.scalars(query)}

    async def open_rows(self, limit: int) -> list[tuple[Dispute, Order]]:
        query = (
            select(Dispute, Order)
            .join(Order, Order.id == Dispute.order_id)
            .where(Dispute.resolved_at.is_(None))
            .order_by(Dispute.id)
            .limit(limit)
        )
        return [(d, o) for d, o in await self._helper.session.execute(query)]

    async def open_order_ids(self, order_ids: Collection[int]) -> set[int]:
        if not order_ids:
            return set()
        query = select(Dispute.order_id).where(
            Dispute.order_id.in_(order_ids), Dispute.resolved_at.is_(None)
        )
        return set(await self._helper.session.scalars(query))

    async def expired_order_ids(self, now: datetime) -> list[int]:
        query = (
            select(Dispute.order_id)
            .where(Dispute.resolved_at.is_(None), Dispute.awaiting_until < now)
            .order_by(Dispute.id)
        )
        return list(await self._helper.session.scalars(query))

    async def ending_order_ids(self, until: datetime, now: datetime) -> list[int]:
        query = (
            select(Dispute.order_id)
            .where(
                Dispute.resolved_at.is_(None),
                Dispute.awaiting_until > now,
                Dispute.awaiting_until <= until,
            )
            .order_by(Dispute.id)
        )
        return list(await self._helper.session.scalars(query))
