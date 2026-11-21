from app.domain.enums.order import OrderStatus

ALLOWED: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.awaiting_input: {OrderStatus.paid, OrderStatus.cancelled},
    OrderStatus.paid: {OrderStatus.in_queue, OrderStatus.completed, OrderStatus.failed},
    OrderStatus.in_queue: {OrderStatus.assigned, OrderStatus.cancelled, OrderStatus.failed},
    OrderStatus.assigned: {OrderStatus.in_queue, OrderStatus.ready, OrderStatus.failed},
    OrderStatus.ready: {OrderStatus.completed, OrderStatus.assigned, OrderStatus.failed},
    OrderStatus.completed: {OrderStatus.refunded},
    OrderStatus.failed: {OrderStatus.refunded},
    OrderStatus.refunded: set(),
    OrderStatus.cancelled: set(),
}


class InvalidTransition(Exception):  # noqa: N818
    pass


def ensure_transition(current: OrderStatus, new: OrderStatus) -> None:
    if new not in ALLOWED[current]:
        raise InvalidTransition(f"{current} -> {new}")
