import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Final

from app.application.errors.shop import Conflict, InvalidAmount, InvalidField
from app.application.interactors.admin.base import AdminInteractor, apply
from app.application.interactors.balance import parse_money
from app.domain.catalog import Product
from app.domain.promo import PromoCode, PromoCodeUsage

USAGES_LIMIT: Final = 100
MAX_AMOUNT: Final = Decimal("1000000")
MAX_USERS: Final = 1000
_CODE_RE: Final = re.compile(r"[A-Z0-9_\-]{3,32}")
_MONEY: Final = {
    "discount_amount": Decimal("0.01"),
    "bonus_amount": Decimal("0.01"),
    "min_amount": Decimal(0),
}
_KINDS: Final = ("discount_percent", "discount_amount", "bonus_amount")


@dataclass(frozen=True)
class PromoUsageRow:
    usage: PromoCodeUsage
    name: str


def _money(field: str, raw: str | None, *, minimum: Decimal) -> Decimal | None:
    if raw is None or not raw.strip():
        return None
    try:
        value = parse_money(raw)
    except InvalidAmount as e:
        raise InvalidField(field, "at most two decimals") from e
    if not minimum <= value <= MAX_AMOUNT:
        raise InvalidField(field, "out of range")
    return value


@dataclass(frozen=True)
class PromoAdminInteractor(AdminInteractor):
    async def promos(self) -> list[PromoCode]:
        return await self.db.promos()

    async def promo(self, promo_id: int) -> tuple[PromoCode, list[PromoUsageRow]]:
        promo = await self.need(PromoCode, promo_id, lock=False)
        usages = await self.db.promo_usages(promo_id, USAGES_LIMIT)
        names = await self.db.user_names([u.user_id for u in usages])
        return promo, [PromoUsageRow(u, names.get(u.user_id, "")) for u in usages]

    async def _values(self, fields: dict[str, Any]) -> dict[str, Any]:  # noqa: C901
        """Column values of the fields that were sent, validated one by one."""
        out: dict[str, Any] = {}
        if "discount_percent" in fields:
            percent = fields["discount_percent"]
            if percent is not None and not 1 <= percent <= 100:
                raise InvalidField("discount_percent", "1..100")
            out["discount_percent"] = percent
        for name, minimum in _MONEY.items():
            if name in fields:
                out[name] = _money(name, fields[name], minimum=minimum)
        if "usage_limit" in fields:
            limit = fields["usage_limit"]
            if limit is not None and not 1 <= limit <= 10_000_000:
                raise InvalidField("usage_limit", "at least 1")
            out["usage_limit"] = limit
        if "expires_at" in fields:
            expires: datetime | None = fields["expires_at"]
            if expires is not None and expires.tzinfo is None:
                raise InvalidField("expires_at", "needs a time zone")
            out["expires_at"] = expires
        if "product_id" in fields:
            if fields["product_id"] is not None:
                await self.need(Product, fields["product_id"], lock=False)
            out["product_id"] = fields["product_id"]
        out |= self._audience(fields)
        return out

    @staticmethod
    def _audience(fields: dict[str, Any]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        if "allowed_user_ids" in fields:
            ids = sorted(set(fields["allowed_user_ids"] or []))
            if len(ids) > MAX_USERS or any(i <= 0 for i in ids):
                raise InvalidField("allowed_user_ids", "positive Telegram ids, at most 1000")
            out["allowed_user_ids"] = ids
        for flag in ("new_users_only", "reusable", "active"):
            if flag in fields:
                out[flag] = bool(fields[flag])
        return out

    @staticmethod
    def _one_kind(values: dict[str, Any]) -> None:
        if sum(values.get(k) is not None for k in _KINDS) != 1:
            raise InvalidField("kind", "exactly one of percent, amount, bonus")

    async def create(self, actor: int, code: str, fields: dict[str, Any]) -> PromoCode:
        code = code.strip().upper()
        if not _CODE_RE.fullmatch(code):
            raise InvalidField("code", "A-Z, 0-9, _ and -; 3-32 characters")
        async with self.tx():
            values = await self._values(fields)
            self._one_kind(values)
            if await self.db.promo_by_code(code) is not None:
                raise Conflict("code_taken")
            promo = PromoCode(code=code, **values)
            await self.db.add(promo)
            await self.db.audit(actor, "promo.create", f"promo:{promo.id}", {"code": code})
        return promo

    async def update(self, actor: int, promo_id: int, fields: dict[str, Any]) -> PromoCode:
        async with self.tx():
            promo = await self.need(PromoCode, promo_id)
            values = await self._values(fields)
            kinds = {k: getattr(promo, k) for k in _KINDS} | {
                k: v for k, v in values.items() if k in _KINDS
            }
            self._one_kind(kinds)
            limit = values.get("usage_limit", promo.usage_limit)
            if limit is not None and limit < promo.times_used:
                raise InvalidField("usage_limit", "below the number of uses so far")
            diff = apply(promo, values)
            await self.db.audit(actor, "promo.update", f"promo:{promo_id}", diff)
        return promo
