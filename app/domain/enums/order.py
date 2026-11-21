from enum import StrEnum


class OrderStatus(StrEnum):
    awaiting_input = "awaiting_input"
    paid = "paid"
    in_queue = "in_queue"
    assigned = "assigned"
    ready = "ready"
    completed = "completed"
    failed = "failed"
    refunded = "refunded"
    cancelled = "cancelled"
