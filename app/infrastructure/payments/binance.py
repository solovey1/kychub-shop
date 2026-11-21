import hashlib
import hmac
import time
from decimal import Decimal, InvalidOperation
from typing import Any, ClassVar

from aiohttp import ClientSession

from app.application.ports.payments import CreatedPayment
from app.domain.enums.ledger import PaymentStatus

BASE_URL = "https://api.binance.com"
HISTORY_LIMIT = 100


class BinancePayGateway:
    """No invoices: the buyer sends USDT to our Pay ID with the payment id as the note."""

    code: ClassVar[str] = "binance"

    def __init__(self, http: ClientSession, api_key: str, api_secret: str) -> None:
        self.http = http
        self.api_key = api_key
        self.api_secret = api_secret.encode()

    async def create_payment(
        self, amount: Decimal, payment_id: str, description: str
    ) -> CreatedPayment:
        return CreatedPayment(pay_id=payment_id, url=None)

    async def get_status(self, pay_id: str, amount: Decimal) -> PaymentStatus:
        params: dict[str, Any] = {"limit": HISTORY_LIMIT, "timestamp": int(time.time() * 1000)}
        query = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
        params["signature"] = hmac.new(self.api_secret, query.encode(), hashlib.sha256).hexdigest()
        async with self.http.get(
            f"{BASE_URL}/sapi/v1/pay/transactions",
            params=params,
            headers={"X-MBX-APIKEY": self.api_key},
        ) as response:
            body = await response.json()
            if response.status != 200:
                raise RuntimeError(f"Binance Pay error {response.status}: {body}")
        for tx in body.get("data") or []:
            if pay_id not in (tx.get("note") or "") or tx.get("currency") != "USDT":
                continue
            try:
                received = Decimal(str(tx["amount"]))
            except (KeyError, InvalidOperation):
                continue
            if received >= amount:  # outgoing transfers are negative
                return PaymentStatus.success
        return PaymentStatus.created
