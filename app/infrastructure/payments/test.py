from decimal import Decimal
from typing import ClassVar

from app.application.ports.payments import CreatedPayment
from app.domain.enums.ledger import PaymentStatus


class TestGateway:
    """Pays instantly. Enabled only by COMMON_TEST_PAYMENTS."""

    __test__ = False  # not a pytest class
    code: ClassVar[str] = "test"

    async def create_payment(
        self, amount: Decimal, payment_id: str, description: str
    ) -> CreatedPayment:
        return CreatedPayment(pay_id=payment_id, url=None)

    async def get_status(self, pay_id: str, amount: Decimal) -> PaymentStatus:
        return PaymentStatus.success
