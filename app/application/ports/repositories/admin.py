from decimal import Decimal
from typing import Any, NamedTuple, Protocol

from app.domain.base import Base
from app.domain.catalog import Category, Country, Product, ProductVariant, Service, StockUnit
from app.domain.enums.order import OrderStatus
from app.domain.executor import ExecutorProfile
from app.domain.ledger import LedgerEntry
from app.domain.order import Order
from app.domain.user import User


class ExecutorRow(NamedTuple):
    profile: ExecutorProfile
    in_work: int  # assigned + ready
    completed: int
    avg_score: float | None


class AdminGateway(Protocol):
    """Everything the admin panel reads and writes that the shop flows do not. Nothing here
    commits: the interactor owns the transaction."""

    async def get[T: Base](self, model: type[T], pk: object) -> T | None: ...

    async def lock[T: Base](self, model: type[T], pk: object) -> T | None:
        """`SELECT ... FOR UPDATE` with fresh column values."""

    async def add(self, *items: Base) -> None:
        """Insert and flush, so generated ids are available."""

    async def delete(self, item: Base) -> None: ...

    async def flush(self) -> None: ...

    async def audit(
        self, actor_id: int, action: str, target: str | None, payload: dict[str, Any]
    ) -> None: ...

    # --- catalog
    async def categories(self) -> list[Category]:
        """All of them, active or not, in tree order (position, id)."""

    async def category_counts(self) -> dict[int, tuple[int, int]]:
        """category id -> (child categories, products)."""

    async def products_of(self, category_id: int) -> list[tuple[Product, int, Decimal | None]]:
        """(product, variants, cheapest active price) in display order."""

    async def variants_of(self, product_id: int) -> list[ProductVariant]: ...

    async def free_stock(self, variant_ids: list[int]) -> dict[int, int]:
        """Unsold, limited units per variant."""

    async def product_used(self, product_id: int) -> str | None:
        """Why the product may not be deleted: `has_orders`, `has_promo`, or None."""

    async def variant_has_orders(self, variant_id: int) -> bool: ...

    async def services(self) -> list[Service]: ...

    async def service_products(self, service_id: int) -> int: ...

    async def service_by_code(self, code: str) -> Service | None: ...

    async def countries(self) -> list[Country]: ...

    async def country_used(self, code: str) -> bool:
        """Some variant or executor permission refers to it."""

    async def stock_recent(self, variant_id: int, limit: int) -> list[StockUnit]:
        """Newest unsold limited units first."""

    async def stock_unlimited(self, variant_id: int) -> StockUnit | None: ...

    async def stock_payloads(self, variant_id: int, payloads: list[str]) -> set[str]:
        """Which of these payloads are already waiting unsold."""

    # --- people
    async def users_search(self, text: str, limit: int) -> list[User]:
        """By Telegram id (digits) or part of the name, newest first."""

    async def orders_of_user(self, user_id: int, limit: int) -> list[Order]: ...

    async def executor_rows(self) -> list[ExecutorRow]: ...

    async def managers(self) -> list[User]:
        """Everybody with the manager role."""

    async def user_names(self, ids: list[int]) -> dict[int, str]: ...

    async def executor_aliases(self, ids: list[int]) -> dict[int, str]: ...

    # --- orders
    async def orders_filtered(
        self,
        status: OrderStatus | None,
        product_id: int | None,
        user_id: int | None,
        executor_id: int | None,
        offset: int,
        limit: int,
    ) -> tuple[list[Order], int]:
        """Newest first, and the total that matches."""

    async def entries_for_order(self, order_id: int) -> list[LedgerEntry]: ...

    async def assignable(
        self, service_id: int, country_code: str | None
    ) -> list[tuple[ExecutorProfile, int]]:
        """Active executors permitted for the service and country, with their load."""
