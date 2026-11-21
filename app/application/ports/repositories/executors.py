from typing import NamedTuple, Protocol

from app.domain.audit import AuditLog
from app.domain.catalog import Service
from app.domain.executor import ExecutorProfile
from app.domain.ledger import LedgerEntry, Withdrawal
from app.domain.review import OrderReview


class Candidate(NamedTuple):
    user_id: int
    load: int  # assigned + ready orders
    completed: int


class StatsRow(NamedTuple):
    completed: int
    failed: int
    overdue: int
    refused: int
    avg_minutes: float | None
    avg_score: float | None


class ExecutorsGateway(Protocol):
    async def get_profile(self, user_id: int) -> ExecutorProfile | None: ...

    async def get_profile_for_update(self, user_id: int) -> ExecutorProfile | None:
        """Serialises everything that changes this executor's load."""

    async def get_by_alias(self, alias: str) -> ExecutorProfile | None: ...

    async def add_profile(self, profile: ExecutorProfile) -> None:
        """Insert and flush."""

    async def permission_rows(self, executor_id: int) -> list[tuple[Service, str]]:
        """(service, country code) pairs the executor is allowed to work with."""

    async def replace_permissions(
        self, executor_id: int, service_id: int, country_codes: list[str]
    ) -> None:
        """Replace the executor's permissions for one service."""

    async def add_audit(self, record: AuditLog) -> None: ...

    async def staff_ids(self) -> list[int]:
        """Users with the admin or manager role."""

    async def candidates(
        self,
        service_id: int,
        country_code: str | None,
        exclude: set[int],
        only: int | None = None,
    ) -> list[Candidate]:
        """Active executors permitted for the service and country (any country when None)
        with load below their limit, least loaded first, then most completed orders."""

    async def review_exists(self, order_id: int) -> bool: ...

    async def add_review(self, review: OrderReview) -> None:
        """Insert and flush."""

    async def stats(self, executor_id: int) -> StatsRow: ...

    async def add_withdrawal(self, withdrawal: Withdrawal) -> None:
        """Insert and flush, so `withdrawal.id` is available."""

    async def wallet_entries(self, user_id: int, limit: int) -> list[LedgerEntry]:
        """Latest ledger entries of the executor hold and available accounts."""
