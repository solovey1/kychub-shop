from dataclasses import dataclass
from typing import Any, ClassVar

from app.domain.catalog import Product
from app.domain.order import Order


@dataclass(frozen=True)
class ManualFulfillment:
    code: ClassVar[str] = "manual"

    def validate_config(self, config: dict[str, Any]) -> None:
        return None

    async def on_paid(self, order: Order, product: Product) -> None:
        return None  # stays `paid` until an admin picks it up
