"""The two changes of an open dispute that other interactors make under the order lock."""

from app.application.ports.repositories.disputes import DisputesGateway
from app.application.ports.repositories.orders import OrdersGateway
from app.domain.dispute import Dispute
from app.domain.enums.dispute import DisputeResolution
from app.domain.order import Order, OrderEvent
from app.utils.time import datetime_now


async def close_dispute(
    disputes: DisputesGateway,
    orders: OrdersGateway,
    order: Order,
    resolution: DisputeResolution,
    by: int | None,
) -> Dispute | None:
    """Closes the open dispute of the order, if any. The caller holds the order lock and commits.
    Whoever completes, sends back or refunds an order calls this in the same transaction, so a
    dispute never outlives the decision that settled it. `by` None: the system."""
    dispute = await disputes.open_for_order(order.id)
    if dispute is None:
        return None
    dispute.resolved_at = datetime_now()
    dispute.resolution = resolution
    dispute.resolved_by = by
    dispute.awaiting_role = None
    dispute.awaiting_until = None
    await orders.add_event(
        OrderEvent(
            order_id=order.id,
            actor_id=by,
            type="dispute_resolved",
            payload={"dispute_id": dispute.id, "resolution": resolution.value},
        )
    )
    return dispute


async def reply_seen(
    disputes: DisputesGateway, orders: OrdersGateway, order_id: int, side: str
) -> None:
    """The side the dispute waits for wrote in the order chat: it stops waiting. Takes the order
    lock first (the one the auto-resolve job takes) and reads the dispute again under it, so a
    message a moment before the deadline either clears the wait or finds the dispute already
    resolved, never both."""
    dispute = await disputes.open_for_order(order_id)
    if dispute is None or dispute.awaiting_role != side:
        return
    await orders.get_for_update(order_id)
    dispute = await disputes.open_for_order(order_id)
    if dispute is not None and dispute.awaiting_role == side:
        dispute.awaiting_role = None
        dispute.awaiting_until = None
