from dataclasses import dataclass
from decimal import Decimal

from app.application.errors.shop import PromoError
from app.application.interactors.base import BaseInteractor
from app.application.ports.repositories.promo import PromoGateway
from app.domain.money import percent_of
from app.domain.promo import PromoCode
from app.utils.time import datetime_now


def discount_for(promo: PromoCode, price: Decimal) -> Decimal:
    if promo.discount_percent is not None:
        return min(percent_of(price, Decimal(promo.discount_percent)), price)
    return min(promo.discount_amount or Decimal(0), price)


@dataclass(frozen=True)
class PromoService(BaseInteractor):
    gateway: PromoGateway

    @staticmethod
    def _check_kind(
        promo: PromoCode, bonus: bool, amount: Decimal, product_id: int | None
    ) -> None:
        if bonus:
            if promo.bonus_amount is None:
                raise PromoError("not_bonus")
            return
        if promo.bonus_amount is not None:
            raise PromoError("bonus_code")
        if promo.product_id is not None and promo.product_id != product_id:
            raise PromoError("wrong_product")
        if promo.min_amount is not None and amount < promo.min_amount:
            raise PromoError("min_amount")

    async def check(
        self,
        user_id: int,
        code: str,
        *,
        bonus: bool,
        amount: Decimal = Decimal(0),
        product_id: int | None = None,
        lock: bool = False,
    ) -> PromoCode:
        """Validate a promo code for `user_id`. With `lock=True` the row is held FOR UPDATE until
        the caller commits. Raises PromoError(code)."""
        promo = await self.gateway.get_by_code(code.strip().upper(), lock)
        if promo is None or not promo.active:
            raise PromoError("not_found")
        if promo.expires_at is not None and promo.expires_at <= datetime_now():
            raise PromoError("expired")
        if promo.usage_limit is not None and promo.times_used >= promo.usage_limit:
            raise PromoError("exhausted")
        self._check_kind(promo, bonus, amount, product_id)
        if promo.allowed_user_ids and user_id not in promo.allowed_user_ids:
            raise PromoError("not_allowed")
        if promo.new_users_only and await self.gateway.has_purchases(user_id):
            raise PromoError("new_users_only")
        if not promo.reusable and await self.gateway.usage_exists(promo.id, user_id):
            raise PromoError("already_used")
        return promo
