from collections.abc import Collection
from datetime import datetime
from typing import Protocol

from app.domain.dispute import Dispute
from app.domain.order import Order


class DisputesGateway(Protocol):
    async def add(self, dispute: Dispute) -> None:
        """Insert and flush."""

    async def open_for_order(self, order_id: int) -> Dispute | None:
        """The open dispute of the order with fresh column values (decisions are made under the
        order lock, and another transaction may have changed it a moment ago)."""

    async def open_rows(self, limit: int) -> list[tuple[Dispute, Order]]:
        """Open disputes with their orders, oldest first."""

    async def open_order_ids(self, order_ids: Collection[int]) -> set[int]:
        """Of these orders, the ones with an open dispute."""

    async def expired_order_ids(self, now: datetime) -> list[int]:
        """Orders whose open dispute waits for an answer past its deadline."""

    async def ending_order_ids(self, until: datetime, now: datetime) -> list[int]:
        """Orders whose open dispute waits for an answer and the deadline is in (now, until]."""
