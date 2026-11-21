from typing import Protocol

from app.domain.promo import PromoCode, PromoCodeUsage


class PromoGateway(Protocol):
    async def get_by_code(self, code: str, lock: bool) -> PromoCode | None:
        """`lock=True` takes SELECT ... FOR UPDATE on the promo row."""

    async def usage_exists(self, promo_id: int, user_id: int) -> bool: ...

    async def has_purchases(self, user_id: int) -> bool: ...

    async def add_usage(self, usage: PromoCodeUsage) -> None: ...
