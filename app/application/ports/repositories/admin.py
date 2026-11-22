from decimal import Decimal
from typing import Any, Protocol

from app.domain.base import Base
from app.domain.catalog import Category, Country, Product, ProductVariant, Service, StockUnit


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
