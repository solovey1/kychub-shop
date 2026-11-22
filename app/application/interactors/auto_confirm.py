import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Final

from app.application.interactors.base import BaseInteractor
from app.application.interactors.order_review import OrderReviewInteractor
from app.application.ports.repositories.orders import OrdersGateway
from app.application.ports.repositories.settings import SettingsGateway
from app.application.ports.uow import UnitOfWork
from app.application.settings_keys import CONFIRM_HOURS, DEFAULT_CONFIRM_HOURS
from app.domain.enums.order import OrderStatus
from app.domain.order import Order, OrderEvent
from app.utils.time import datetime_now

logger: Final = logging.getLogger(__name__)

REMIND_BEFORE: Final = timedelta(hours=2)


async def confirm_hours(settings: SettingsGateway) -> int:
    return int(await settings.get(CONFIRM_HOURS, DEFAULT_CONFIRM_HOURS))


def confirm_deadline(order: Order, hours: int) -> datetime | None:
    """When a `ready` order confirms itself, or None (not ready)."""
    if order.status is not OrderStatus.ready or order.ready_at is None:
        return None
    return order.ready_at + timedelta(hours=hours)


@dataclass(frozen=True)
class AutoConfirmInteractor(BaseInteractor):
    """The buyer has `confirm_hours` to check a submitted order; then the system confirms it."""

    uow: UnitOfWork
    orders: OrdersGateway
    settings: SettingsGateway
    review: OrderReviewInteractor

    async def confirm_due(self) -> list[Order]:
        """Every order in its own transaction; a broken one does not stop the rest."""
        done: list[Order] = []
        hours = await confirm_hours(self.settings)
        for candidate in await self.orders.ready_before(datetime_now() - timedelta(hours=hours)):
            try:
                order = await self.orders.get_for_update(candidate.id)
                deadline = confirm_deadline(order, hours) if order else None
                if order is None or deadline is None or deadline >= datetime_now():
                    await self.uow.rollback()  # confirmed, sent back or disputed meanwhile
                    continue
                await self.review.complete_locked(order, None)
                await self.orders.add_event(OrderEvent(order_id=order.id, type="auto_confirmed"))
                await self.uow.commit()
                done.append(order)
            except Exception:
                await self.uow.rollback()
                logger.exception("auto-confirming order %s failed", candidate.id)
        return done

    async def remind_due(self) -> list[Order]:
        """The buyer gets one message 2 hours before the auto-confirmation. The event is committed
        first (a crash loses one message, never sends two); it carries `ready_at`, so a sent-back
        and re-submitted order is reminded again. No reminder when the whole term is 2 hours or
        less."""
        found: list[Order] = []
        hours = await confirm_hours(self.settings)
        if timedelta(hours=hours) <= REMIND_BEFORE:
            return found
        cutoff = datetime_now() - timedelta(hours=hours) + REMIND_BEFORE
        for candidate in await self.orders.ready_before(cutoff):
            try:
                order = await self.orders.get_for_update(candidate.id)
                deadline = confirm_deadline(order, hours) if order else None
                now = datetime_now()
                if (
                    order is None
                    or deadline is None
                    or deadline - REMIND_BEFORE > now
                    or deadline <= now
                ):
                    await self.uow.rollback()
                    continue
                assert order.ready_at is not None
                stamp = order.ready_at.isoformat()
                if any(
                    e.type == "confirm_reminder" and e.payload.get("ready_at") == stamp
                    for e in await self.orders.events(order.id)
                ):
                    await self.uow.rollback()
                    continue
                await self.orders.add_event(
                    OrderEvent(
                        order_id=order.id, type="confirm_reminder", payload={"ready_at": stamp}
                    )
                )
                await self.uow.commit()
                found.append(order)
            except Exception:
                await self.uow.rollback()
                logger.exception("recording the confirm reminder of order %s failed", candidate.id)
        return found
