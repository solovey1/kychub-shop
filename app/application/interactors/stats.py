from dataclasses import dataclass

from app.application.interactors.base import BaseInteractor
from app.application.ports.repositories.executors import ExecutorsGateway


@dataclass(frozen=True)
class Stats:
    completed: int
    failed: int
    overdue: int
    refused: int
    avg_minutes: float | None
    avg_score: float | None


@dataclass(frozen=True)
class ExecutorStats(BaseInteractor):
    """Computed on request from orders, events and ratings; no cache."""

    executors: ExecutorsGateway

    async def stats(self, executor_id: int) -> Stats:
        return Stats(*await self.executors.stats(executor_id))

    async def for_buyer(self, user_id: int) -> list[tuple[str, int]]:
        """Executor aliases and how many orders each one completed for this buyer."""
        return await self.executors.buyer_executors(user_id)
