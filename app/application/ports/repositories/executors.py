from typing import Protocol

from app.domain.audit import AuditLog
from app.domain.catalog import Service
from app.domain.executor import ExecutorProfile


class ExecutorsGateway(Protocol):
    async def get_profile(self, user_id: int) -> ExecutorProfile | None: ...

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
