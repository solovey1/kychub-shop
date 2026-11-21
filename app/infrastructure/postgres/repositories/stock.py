from dataclasses import dataclass

from sqlalchemy import select

from app.application.ports.repositories.stock import StockGateway
from app.domain.catalog import StockUnit
from app.infrastructure.postgres.repository_helper import SqlRepositoryHelper


@dataclass
class StockRepository(StockGateway):
    _helper: SqlRepositoryHelper[StockUnit]

    async def take(self, variant_id: int, order_id: int) -> StockUnit | None:
        session = self._helper.session
        unit = await session.scalar(
            select(StockUnit)
            .where(
                StockUnit.variant_id == variant_id,
                StockUnit.sold_order_id.is_(None),
                StockUnit.is_unlimited.is_(False),
            )
            .order_by(StockUnit.id)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        if unit is not None:
            unit.sold_order_id = order_id
            return unit
        unlimited: StockUnit | None = await session.scalar(
            select(StockUnit)
            .where(StockUnit.variant_id == variant_id, StockUnit.is_unlimited.is_(True))
            .limit(1)
        )
        return unlimited
