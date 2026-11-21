import logging
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Final, Literal

from app.application.cards import OrderCard
from app.application.errors.shop import OrderUnavailable
from app.application.fulfillment.base import move
from app.application.interactors.base import BaseInteractor
from app.application.interactors.cards import CardBuilder, OrderContext, load_context
from app.application.ports.repositories.catalog import CatalogGateway
from app.application.ports.repositories.executors import Candidate, ExecutorsGateway
from app.application.ports.repositories.orders import OrdersGateway
from app.application.ports.uow import UnitOfWork
from app.domain.enums.catalog import AssignMode
from app.domain.enums.order import OrderStatus
from app.domain.order import Order, OrderEvent
from app.utils.time import datetime_now

logger: Final = logging.getLogger(__name__)

STALE_AFTER: Final = timedelta(minutes=10)
QUEUE_LIMIT: Final = 50
QUEUE_SCAN: Final = 200


@dataclass(frozen=True)
class DispatchResult:
    """What the caller has to tell people after the commit.

    offer: send the proposal to `executor_ids`; assigned: tell the only id in `executor_ids`;
    none: nobody is available; skipped: the order is no longer waiting in the queue.
    """

    order_id: int
    kind: Literal["offer", "assigned", "none", "skipped"]
    executor_ids: list[int] = field(default_factory=list)
    first_no_executor: bool = False
    released_executor_id: int | None = None  # who lost the order just before this dispatch
    release_reason: Literal["refused", "overdue"] | None = None


@dataclass(frozen=True)
class DispatchInteractor(BaseInteractor):
    uow: UnitOfWork
    orders: OrdersGateway
    executors: ExecutorsGateway
    catalog: CatalogGateway
    cards: CardBuilder

    async def queue_for(self, executor_id: int) -> list[OrderCard]:
        """The waiting orders this executor may take now (permission, limit, not refused).
        ponytail: scans the oldest 200 queued orders, one check each; index it when the queue
        grows past that."""
        found: list[OrderCard] = []
        for order in await self.orders.queue(QUEUE_SCAN):
            ctx = await load_context(self.catalog, order)
            if await self._candidates(order, ctx, only=executor_id):
                found.append(await self.cards.build(order, executor_id))
                if len(found) == QUEUE_LIMIT:
                    break
        return found

    async def eligible(self, order_id: int) -> list[int]:
        order = await self.orders.get(order_id)
        if order is None:
            return []
        ctx = await load_context(self.catalog, order)
        return [c.user_id for c in await self._candidates(order, ctx)]

    async def dispatch(self, order_id: int) -> DispatchResult:
        try:
            order = await self.orders.get_for_update(order_id)
            if order is None:
                return DispatchResult(order_id, "skipped")
            result = await self._dispatch(order)
            await self.uow.commit()
            return result
        except BaseException:
            await self.uow.rollback()
            raise

    async def take(self, executor_id: int, order_id: int) -> bool:
        """False when the order is gone, taken, or the executor may not (permission, limit)."""
        try:
            order = await self.orders.get_for_update(order_id)
            if order is None or order.status is not OrderStatus.in_queue or order.executor_id:
                await self.uow.rollback()
                return False
            # the profile lock serialises the limit check of one executor across orders
            if await self.executors.get_profile_for_update(executor_id) is None:
                await self.uow.rollback()
                return False
            ctx = await load_context(self.catalog, order)
            if not await self._candidates(order, ctx, only=executor_id):
                await self.uow.rollback()
                return False
            assert ctx is not None and ctx.service is not None  # a candidate implies both
            await self._assign(order, ctx, executor_id, "queue")
            await self.uow.commit()
            return True
        except BaseException:
            await self.uow.rollback()
            raise

    async def refuse(self, executor_id: int, order_id: int) -> DispatchResult:
        try:
            order = await self.orders.get_for_update(order_id)
            if (
                order is None
                or order.status is not OrderStatus.assigned
                or order.executor_id != executor_id
            ):
                raise OrderUnavailable(order_id)
            await self._release(order, "refused", executor_id)
            result = await self._dispatch(order, released=(executor_id, "refused"))
            await self.uow.commit()
            return result
        except BaseException:
            await self.uow.rollback()
            raise

    async def expire_overdue(self) -> list[DispatchResult]:
        """Every order in its own transaction; a broken one does not stop the rest."""
        results: list[DispatchResult] = []
        for order_id in await self.orders.overdue_ids(datetime_now()):
            try:
                order = await self.orders.get_for_update(order_id)
                now = datetime_now()
                if (
                    order is None
                    or order.status is not OrderStatus.assigned  # submitted or refused meanwhile
                    or order.executor_id is None
                    or order.deadline_at is None
                    or order.deadline_at >= now
                ):
                    await self.uow.rollback()
                    continue
                executor_id = order.executor_id
                await self._release(order, "overdue", executor_id)
                result = await self._dispatch(order, released=(executor_id, "overdue"))
                await self.uow.commit()
                results.append(result)
            except Exception:
                await self.uow.rollback()
                logger.exception("expiring order %s failed", order_id)
        return results

    async def requeue_stale(self) -> list[DispatchResult]:
        results: list[DispatchResult] = []
        for order_id in await self.orders.stale_ids(datetime_now() - STALE_AFTER):
            try:
                result = await self.dispatch(order_id)
            except Exception:
                logger.exception("re-dispatching order %s failed", order_id)
                continue
            if result.kind != "skipped":
                results.append(result)
        return results

    async def _candidates(
        self, order: Order, ctx: OrderContext | None, only: int | None = None
    ) -> list[Candidate]:
        if ctx is None or ctx.service is None:
            return []
        exclude = await self.orders.excluded_executor_ids(order.id)
        return await self.executors.candidates(
            ctx.service.id, ctx.variant.country_code, exclude, only
        )

    async def _release(
        self, order: Order, reason: Literal["refused", "overdue"], executor_id: int
    ) -> None:
        """assigned -> in_queue and the event that keeps this executor out of the next round."""
        await move(
            self.orders, order, OrderStatus.in_queue, executor_id if reason == "refused" else None
        )
        order.executor_id = None
        order.assigned_at = None
        order.deadline_at = None
        await self.orders.add_event(
            OrderEvent(
                order_id=order.id,
                actor_id=executor_id if reason == "refused" else None,
                type=reason,
                payload={"executor_id": executor_id},
            )
        )

    async def _assign(
        self, order: Order, ctx: OrderContext, executor_id: int, mode: Literal["queue", "auto"]
    ) -> None:
        assert ctx.service is not None
        now = datetime_now()
        order.executor_id = executor_id  # first: move() flushes and the CHECK needs the executor
        await move(self.orders, order, OrderStatus.assigned, executor_id)
        order.assigned_at = now
        order.deadline_at = now + timedelta(minutes=ctx.service.deadline_minutes)
        await self.orders.add_event(
            OrderEvent(
                order_id=order.id,
                actor_id=executor_id,
                type="assigned",
                payload={"executor_id": executor_id, "mode": mode},
            )
        )

    async def _dispatch(
        self,
        order: Order,
        released: tuple[int, Literal["refused", "overdue"]] | None = None,
    ) -> DispatchResult:
        """Runs under the order lock, commits nothing."""
        lost, reason = released if released else (None, None)
        if order.status is not OrderStatus.in_queue or order.executor_id is not None:
            return DispatchResult(order.id, "skipped")
        ctx = await load_context(self.catalog, order)
        candidates = await self._candidates(order, ctx)
        if candidates and ctx is not None and ctx.service is not None:
            if ctx.service.assign_mode is AssignMode.queue:
                await self._event(order, "dispatch", {"mode": "queue", "count": len(candidates)})
                ids = [c.user_id for c in candidates]
                return DispatchResult(order.id, "offer", ids, False, lost, reason)
            for candidate in candidates:  # least loaded first
                await self.executors.get_profile_for_update(candidate.user_id)
                if await self._candidates(order, ctx, only=candidate.user_id):
                    await self._assign(order, ctx, candidate.user_id, "auto")
                    await self._event(order, "dispatch", {"mode": "auto"})
                    return DispatchResult(
                        order.id, "assigned", [candidate.user_id], False, lost, reason
                    )
        first = not await self.orders.has_event(order.id, "no_executor")
        await self._event(order, "dispatch", {"mode": "none"})
        if first:
            await self._event(order, "no_executor", {})
        return DispatchResult(order.id, "none", [], first, lost, reason)

    async def _event(self, order: Order, event_type: str, payload: dict[str, object]) -> None:
        await self.orders.add_event(
            OrderEvent(order_id=order.id, type=event_type, payload=payload)
        )
