from dataclasses import dataclass
from decimal import Decimal

from app.application.interactors.ledger import LedgerService
from app.application.ports.repositories.ledger import LedgerGateway
from app.domain.enums.ledger import LedgerAccount, LedgerKind
from app.domain.enums.order import OrderStatus
from app.domain.order import Order


@dataclass(frozen=True)
class Refunded:
    """Outcome of a refund or a cancellation, for the notifications sent after the commit."""

    order_id: int
    buyer_id: int
    executor_id: int | None
    amount: Decimal
    was: OrderStatus  # the status the order had before it was closed


def order_ref(order: Order) -> str:
    return f"order:{order.id}"


async def open_hold(gateway: LedgerGateway, order: Order) -> bool:
    """The order holds buyer funds that were neither captured nor released yet."""
    ref = order_ref(order)
    uid, acc = order.user_id, LedgerAccount.buyer_hold
    if await gateway.get_by_ref(uid, acc, LedgerKind.order_hold, ref) is None:
        return False
    return (
        await gateway.get_by_ref(uid, acc, LedgerKind.order_capture, ref) is None
        and await gateway.get_by_ref(uid, acc, LedgerKind.order_release, ref) is None
    )


async def capture_buyer(ledger: LedgerService, gateway: LedgerGateway, order: Order) -> bool:
    """The order is done: the held money is spent for good. Under the order lock; a second call
    (or an order that never held anything) posts nothing."""
    if not await open_hold(gateway, order):
        return False
    await ledger.post(
        order.user_id,
        LedgerAccount.buyer_hold,
        -(order.price - order.discount),
        LedgerKind.order_capture,
        order_id=order.id,
        ref=order_ref(order),
    )
    return True


async def refund_buyer(ledger: LedgerService, gateway: LedgerGateway, order: Order) -> Decimal:
    """Everything the buyer actually paid goes back to the balance. Idempotent per order.
    Money still in the hold is released first; after the capture only the refund is left."""
    total = order.price - order.discount
    if total > 0:
        if await open_hold(gateway, order):
            await ledger.post(
                order.user_id,
                LedgerAccount.buyer_hold,
                -total,
                LedgerKind.order_release,
                order_id=order.id,
                ref=order_ref(order),
            )
        await ledger.post(
            order.user_id,
            LedgerAccount.main,
            total,
            LedgerKind.refund,
            order_id=order.id,
            ref=order_ref(order),
        )
    return total


async def reverse_earning(ledger: LedgerService, gateway: LedgerGateway, order: Order) -> bool:
    """Take the executor accrual back while it is still in hold. After the hold has been
    released the accrual is final and the refund is paid by the shop."""
    if order.executor_id is None:
        return False
    ref = order_ref(order)
    earning = await gateway.get_by_ref(
        order.executor_id, LedgerAccount.executor_hold, LedgerKind.executor_earning, ref
    )
    if earning is None:
        return False
    released = await gateway.get_by_ref(
        order.executor_id, LedgerAccount.executor_hold, LedgerKind.hold_release, ref
    )
    if released is not None:
        return False
    await ledger.post(
        order.executor_id,
        LedgerAccount.executor_hold,
        -earning.amount,
        LedgerKind.earning_reversal,
        order_id=order.id,
        ref=ref,
    )
    return True
