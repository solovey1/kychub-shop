import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Final

from app.application.errors.shop import AlreadyRated, InvalidAmount, InvalidInput, OrderUnavailable
from app.application.interactors.base import BaseInteractor
from app.application.interactors.ledger import LedgerService
from app.application.ports.repositories.executors import ExecutorsGateway
from app.application.ports.repositories.orders import OrdersGateway
from app.application.ports.uow import UnitOfWork
from app.domain.enums.ledger import LedgerAccount, LedgerKind
from app.domain.enums.order import OrderStatus
from app.domain.money import money
from app.domain.order import Order, OrderEvent
from app.domain.review import OrderReview
from app.utils.time import datetime_now

logger: Final = logging.getLogger(__name__)

MAX_TIP: Final = Decimal("1000.00")


@dataclass(frozen=True)
class ReviewInteractor(BaseInteractor):
    uow: UnitOfWork
    orders: OrdersGateway
    executors: ExecutorsGateway

    async def request_due(self) -> list[Order]:
        """Marks due rating requests as sent, one transaction per order, and returns those
        orders for the caller to message. A crash after the commit loses one message at most,
        it never sends two."""
        sent: list[Order] = []
        for order_id in await self.orders.review_due_ids(datetime_now()):
            try:
                order = await self.orders.get_for_update(order_id)
                if (
                    order is None
                    or order.status is not OrderStatus.completed
                    or await self.orders.has_event(order_id, "review_requested")
                ):
                    await self.uow.rollback()
                    continue
                await self.orders.add_event(OrderEvent(order_id=order_id, type="review_requested"))
                await self.uow.commit()
                sent.append(order)
            except Exception:
                await self.uow.rollback()
                logger.exception("marking the rating request of order %s failed", order_id)
        return sent

    async def rate(self, user_id: int, order_id: int, score: int) -> OrderReview:
        """The executor is taken from the order, never from the caller."""
        if not 1 <= score <= 5:
            raise InvalidInput("score")
        try:
            order = await self.orders.get_for_update(order_id)
            if (
                order is None
                or order.user_id != user_id
                or order.status is not OrderStatus.completed
                or order.executor_id is None
            ):
                raise OrderUnavailable(order_id)
            if await self.executors.review_exists(order_id):
                raise AlreadyRated(order_id)
            review = OrderReview(
                order_id=order_id, user_id=user_id, executor_id=order.executor_id, score=score
            )
            await self.executors.add_review(review)
            await self.uow.commit()
            return review
        except BaseException:
            await self.uow.rollback()
            raise


@dataclass(frozen=True)
class TipInteractor(BaseInteractor):
    uow: UnitOfWork
    orders: OrdersGateway
    ledger: LedgerService

    async def tip(self, user_id: int, order_id: int, amount: Decimal, token: str) -> int:
        """Both legs in one transaction. Returns the executor id. The tip is available at once:
        the hold exists for refunds and a tip is never refunded. Repeating a call with the same
        token changes nothing."""
        try:
            amount = money(amount)
        except (ValueError, TypeError) as e:
            raise InvalidAmount(str(amount)) from e
        if not 0 < amount <= MAX_TIP:
            raise InvalidAmount(str(amount))
        try:
            order = await self.orders.get(order_id)
            if (
                order is None
                or order.user_id != user_id
                or order.status is not OrderStatus.completed
                or order.executor_id is None
            ):
                raise OrderUnavailable(order_id)
            ref = f"tip:{order_id}:{token}"
            await self.ledger.post(
                user_id, LedgerAccount.main, -amount, LedgerKind.tip, order_id=order_id, ref=ref
            )
            await self.ledger.post(
                order.executor_id,
                LedgerAccount.executor_available,
                amount,
                LedgerKind.tip,
                order_id=order_id,
                ref=ref,
            )
            await self.uow.commit()
            return order.executor_id
        except BaseException:
            await self.uow.rollback()
            raise
