from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
from typing import Any, Final

from app.application.errors.shop import InvalidAmount, InvalidField
from app.application.interactors.admin.base import AdminInteractor
from app.application.interactors.balance import parse_money
from app.application.ports.repositories.admin import StatsData
from app.application.ports.repositories.settings import SettingsGateway
from app.application.settings_keys import (
    ACCEPT_MINUTES,
    CONFIRM_HOURS,
    DEFAULT_ACCEPT_MINUTES,
    DEFAULT_CONFIRM_HOURS,
    DEFAULT_DISPUTE_REPLY_HOURS,
    DEFAULT_HOLD_DAYS,
    DEFAULT_MIN_WITHDRAWAL,
    DEFAULT_REVIEW_DELAY_HOURS,
    DISPUTE_REPLY_HOURS,
    HOLD_DAYS,
    MIN_WITHDRAWAL,
    REVIEW_DELAY_HOURS,
)
from app.domain.audit import AuditLog
from app.utils.time import datetime_now

PERIODS: Final = (1, 7, 30)
AUDIT_LIMIT: Final = 200


@dataclass(frozen=True)
class StatsAdminInteractor(AdminInteractor):
    async def stats(self, days: int) -> StatsData:
        if days not in PERIODS:
            raise InvalidField("days", "1, 7 or 30")
        return await self.db.stats(datetime_now() - timedelta(days=days))


@dataclass(frozen=True)
class Tunables:
    hold_days: int
    review_delay_hours: int
    min_withdrawal: Decimal
    confirm_hours: int
    dispute_reply_hours: int
    accept_minutes: int


@dataclass(frozen=True)
class SettingsAdminInteractor(AdminInteractor):
    settings: SettingsGateway

    async def get(self) -> Tunables:
        return Tunables(
            int(await self.settings.get(HOLD_DAYS, DEFAULT_HOLD_DAYS)),
            int(await self.settings.get(REVIEW_DELAY_HOURS, DEFAULT_REVIEW_DELAY_HOURS)),
            parse_money(str(await self.settings.get(MIN_WITHDRAWAL, str(DEFAULT_MIN_WITHDRAWAL)))),
            int(await self.settings.get(CONFIRM_HOURS, DEFAULT_CONFIRM_HOURS)),
            int(await self.settings.get(DISPUTE_REPLY_HOURS, DEFAULT_DISPUTE_REPLY_HOURS)),
            int(await self.settings.get(ACCEPT_MINUTES, DEFAULT_ACCEPT_MINUTES)),
        )

    async def update(
        self,
        actor: int,
        hold_days: int,
        review_delay_hours: int,
        min_withdrawal: str,
        confirm_hours: int,
        dispute_reply_hours: int,
        accept_minutes: int,
    ) -> Tunables:
        if not 0 <= hold_days <= 60:
            raise InvalidField("hold_days", "0..60")
        if not 0 <= review_delay_hours <= 720:
            raise InvalidField("review_delay_hours", "0..720")
        if not 1 <= confirm_hours <= 168:
            raise InvalidField("confirm_hours", "1..168")
        if not 1 <= dispute_reply_hours <= 72:
            raise InvalidField("dispute_reply_hours", "1..72")
        if not 1 <= accept_minutes <= 30:
            raise InvalidField("accept_minutes", "1..30")
        try:
            minimum = parse_money(min_withdrawal)
        except InvalidAmount as e:
            raise InvalidField("min_withdrawal", "at most two decimals") from e
        if not Decimal("0.01") <= minimum <= Decimal(100_000):
            raise InvalidField("min_withdrawal", "0.01..100000")
        async with self.tx():
            before = await self.get()
            new: dict[str, Any] = {
                HOLD_DAYS: hold_days,
                REVIEW_DELAY_HOURS: review_delay_hours,
                MIN_WITHDRAWAL: str(minimum),
                CONFIRM_HOURS: confirm_hours,
                DISPUTE_REPLY_HOURS: dispute_reply_hours,
                ACCEPT_MINUTES: accept_minutes,
            }
            old = {
                HOLD_DAYS: before.hold_days,
                REVIEW_DELAY_HOURS: before.review_delay_hours,
                MIN_WITHDRAWAL: str(before.min_withdrawal),
                CONFIRM_HOURS: before.confirm_hours,
                DISPUTE_REPLY_HOURS: before.dispute_reply_hours,
                ACCEPT_MINUTES: before.accept_minutes,
            }
            diff = {k: [old[k], v] for k, v in new.items() if old[k] != v}
            for key, value in new.items():
                await self.db.set_setting(key, value)
            await self.db.audit(actor, "settings.update", None, diff)
        return await self.get()


@dataclass(frozen=True)
class AuditAdminInteractor(AdminInteractor):
    async def rows(
        self, actor_id: int | None, action: str | None
    ) -> list[tuple[AuditLog, str | None]]:
        return await self.db.audit_rows(actor_id, action, AUDIT_LIMIT)

    async def actions(self) -> list[str]:
        return await self.db.audit_actions()
