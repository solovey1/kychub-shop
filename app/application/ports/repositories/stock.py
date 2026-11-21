from typing import Protocol

from app.domain.catalog import StockUnit


class StockGateway(Protocol):
    async def take(self, variant_id: int, order_id: int) -> StockUnit | None:
        """Reserve one unit for the order: an unsold one (row-locked, SKIP LOCKED), else an
        unlimited one. None when nothing is available."""
