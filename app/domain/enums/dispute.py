from enum import StrEnum


class DisputeSide(StrEnum):
    """The two parties of a dispute; also `opened_role` and `awaiting_role`."""

    buyer = "buyer"
    executor = "executor"


class DisputeResolution(StrEnum):
    completed = "completed"  # the order was confirmed
    refunded = "refunded"  # failed, the buyer got the money back
    sent_back = "sent_back"  # returned to the executor
    closed = "closed"  # support closed it, nothing changed
