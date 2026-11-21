import logging
from decimal import Decimal
from typing import ClassVar

from aiocryptopay import AioCryptoPay, Networks  # type: ignore[import-untyped]
from aiocryptopay.const import InvoiceStatus  # type: ignore[import-untyped]

from app.application.ports.payments import CreatedPayment
from app.domain.enums.ledger import PaymentStatus

logger = logging.getLogger(__name__)

INVOICE_TTL = 3600
STATUSES = {
    InvoiceStatus.ACTIVE: PaymentStatus.created,
    InvoiceStatus.PAID: PaymentStatus.success,
    InvoiceStatus.EXPIRED: PaymentStatus.canceled,
}


class CryptoPayGateway:
    code: ClassVar[str] = "cryptobot"

    def __init__(self, token: str, testnet: bool) -> None:
        self.client = AioCryptoPay(
            token, network=Networks.TEST_NET if testnet else Networks.MAIN_NET
        )

    async def close(self) -> None:
        await self.client.close()

    async def create_payment(
        self, amount: Decimal, payment_id: str, description: str
    ) -> CreatedPayment:
        invoice = await self.client.create_invoice(
            amount=str(amount),  # query string; never a float
            asset="USDT",
            description=description,
            payload=payment_id,
            expires_in=INVOICE_TTL,
        )
        return CreatedPayment(pay_id=str(invoice.invoice_id), url=invoice.bot_invoice_url)

    async def get_status(self, pay_id: str, amount: Decimal) -> PaymentStatus:
        invoice = await self.client.get_invoices(invoice_ids=int(pay_id))
        if invoice is None or isinstance(invoice, list):
            return PaymentStatus.created
        status = STATUSES.get(InvoiceStatus(invoice.status))
        if status is None:
            logger.warning("unknown Crypto Pay status %s for invoice %s", invoice.status, pay_id)
            return PaymentStatus.created
        return status
