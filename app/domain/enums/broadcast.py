from enum import StrEnum


class BroadcastStatus(StrEnum):
    draft = "draft"
    sending = "sending"
    sent = "sent"
    failed = "failed"
    stopped = "stopped"
