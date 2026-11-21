from dataclasses import dataclass
from decimal import Decimal
from typing import ClassVar, NewType, Protocol

from app.domain.enums.ledger import PaymentStatus

# Statuses only move forward; a gateway answer with a lower rank is ignored.
STATUS_RANK: dict[PaymentStatus, int] = {
    PaymentStatus.created: 0,
    PaymentStatus.pending: 1,
    PaymentStatus.partially_paid: 1,
    PaymentStatus.canceled: 2,
    PaymentStatus.success: 3,
}


@dataclass(frozen=True)
class CreatedPayment:
    pay_id: str
    url: str | None  # None: show instructions instead of a link (Binance Pay)


class PaymentGateway(Protocol):
    code: ClassVar[str]  # "cryptobot" | "binance" | "nowpayments" | "test"

    async def create_payment(
        self, amount: Decimal, payment_id: str, description: str
    ) -> CreatedPayment: ...

    async def get_status(self, pay_id: str, amount: Decimal) -> PaymentStatus:
        """Raises on gateway errors; callers log and keep the stored status."""
        ...


PaymentGateways = NewType("PaymentGateways", dict[str, PaymentGateway])
