import time
from datetime import timedelta
from decimal import Decimal, InvalidOperation
from typing import Any, ClassVar

from aiohttp import ClientSession

from app.application.ports.payments import CreatedPayment
from app.domain.enums.ledger import PaymentStatus
from app.utils.time import datetime_now

BASE_URL = "https://api.nowpayments.io/v1"
RETURN_URL = "https://t.me"
TOKEN_TTL = 240  # their JWT lives 5 minutes
LOOKBACK = timedelta(days=7)
STATUSES = {
    "waiting": PaymentStatus.created,
    "confirming": PaymentStatus.pending,
    "confirmed": PaymentStatus.pending,
    "sending": PaymentStatus.pending,
    "partially_paid": PaymentStatus.partially_paid,
    "finished": PaymentStatus.success,
    "failed": PaymentStatus.canceled,
    "refunded": PaymentStatus.canceled,
    "expired": PaymentStatus.canceled,
}


class NowPaymentsGateway:
    code: ClassVar[str] = "nowpayments"

    def __init__(self, http: ClientSession, api_key: str, login: str, password: str) -> None:
        self.http = http
        self.api_key = api_key
        self.login = login
        self.password = password
        self._token: str | None = None
        self._token_at = 0.0

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        async with self.http.request(method, f"{BASE_URL}{path}", **kwargs) as response:
            body = await response.json()
            if response.status >= 400:
                raise RuntimeError(f"NOWPayments error {response.status}: {body}")
            return body

    async def _bearer(self) -> str:
        if self._token is None or time.monotonic() - self._token_at > TOKEN_TTL:
            body = await self._request(
                "POST", "/auth", json={"email": self.login, "password": self.password}
            )
            self._token, self._token_at = body["token"], time.monotonic()
        return self._token

    async def create_payment(
        self, amount: Decimal, payment_id: str, description: str
    ) -> CreatedPayment:
        body = await self._request(
            "POST",
            "/invoice",
            headers={"x-api-key": self.api_key},
            json={
                # JSON number: the only float, at the API boundary, always 2 places
                "price_amount": float(amount),
                "price_currency": "USDTBSC",
                "order_id": payment_id,
                "order_description": description,
                "success_url": RETURN_URL,
                "cancel_url": RETURN_URL,
                "is_fixed_rate": False,
                "is_fee_paid_by_user": False,
            },
        )
        return CreatedPayment(pay_id=str(body["id"]), url=body["invoice_url"])

    async def get_status(self, pay_id: str, amount: Decimal) -> PaymentStatus:
        now = datetime_now()
        body = await self._request(
            "GET",
            "/payment",
            headers={"Authorization": f"Bearer {await self._bearer()}", "x-api-key": self.api_key},
            params={
                "limit": 100,
                "page": 0,
                "sortBy": "created_at",
                "orderBy": "desc",
                "dateFrom": (now - LOOKBACK).date().isoformat(),
                "dateTo": (now + timedelta(days=1)).date().isoformat(),
                "invoiceId": pay_id,
            },
        )
        found = [
            self._status(p, amount)
            for p in body.get("data") or []
            if str(p.get("invoice_id")) == pay_id
        ]
        if PaymentStatus.success in found:
            return PaymentStatus.success
        return found[0] if found else PaymentStatus.created  # newest first

    @staticmethod
    def _status(payment: dict[str, Any], amount: Decimal) -> PaymentStatus:
        status = STATUSES.get(str(payment.get("payment_status")), PaymentStatus.created)
        if status is not PaymentStatus.success:
            return status
        try:
            paid = Decimal(str(payment["price_amount"]))
        except (KeyError, InvalidOperation):
            return PaymentStatus.partially_paid
        return PaymentStatus.success if paid >= amount else PaymentStatus.partially_paid
