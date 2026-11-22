from decimal import Decimal
from typing import Final

HOLD_DAYS: Final = "hold_days"
REVIEW_DELAY_HOURS: Final = "review_delay_hours"
MIN_WITHDRAWAL: Final = "min_withdrawal"
CONFIRM_HOURS: Final = "confirm_hours"
DISPUTE_REPLY_HOURS: Final = "dispute_reply_hours"
ACCEPT_MINUTES: Final = "accept_minutes"

DEFAULT_HOLD_DAYS: Final = 3
DEFAULT_REVIEW_DELAY_HOURS: Final = 2
DEFAULT_MIN_WITHDRAWAL: Final = Decimal("10.00")
DEFAULT_CONFIRM_HOURS: Final = 24
DEFAULT_DISPUTE_REPLY_HOURS: Final = 12
DEFAULT_ACCEPT_MINUTES: Final = 3
