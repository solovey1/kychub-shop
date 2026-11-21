from typing import AsyncIterator

from aiohttp import ClientSession, ClientTimeout
from dishka import Provider, Scope, provide

from app.application.models.config import AppConfig
from app.application.ports.payments import PaymentGateway, PaymentGateways
from app.infrastructure.payments.binance import BinancePayGateway
from app.infrastructure.payments.cryptopay import CryptoPayGateway
from app.infrastructure.payments.nowpayments import NowPaymentsGateway
from app.infrastructure.payments.test import TestGateway


class PaymentsProvider(Provider):
    scope = Scope.APP

    @provide
    async def provide_http(self) -> AsyncIterator[ClientSession]:
        async with ClientSession(timeout=ClientTimeout(total=30)) as session:
            yield session

    @provide
    async def provide_gateways(
        self, config: AppConfig, http: ClientSession
    ) -> AsyncIterator[PaymentGateways]:
        cfg = config.payments
        gateways: list[PaymentGateway] = []
        cryptopay: CryptoPayGateway | None = None
        if cfg.cryptopay_token and cfg.cryptopay_enabled:
            cryptopay = CryptoPayGateway(
                cfg.cryptopay_token.get_secret_value(), cfg.cryptopay_network == "testnet"
            )
            gateways.append(cryptopay)
        if cfg.binance_api_key and cfg.binance_api_secret and cfg.binance_enabled:
            gateways.append(
                BinancePayGateway(
                    http,
                    cfg.binance_api_key.get_secret_value(),
                    cfg.binance_api_secret.get_secret_value(),
                )
            )
        if (
            cfg.nowpayments_api_key
            and cfg.nowpayments_login
            and cfg.nowpayments_password
            and cfg.nowpayments_enabled
        ):
            gateways.append(
                NowPaymentsGateway(
                    http,
                    cfg.nowpayments_api_key.get_secret_value(),
                    cfg.nowpayments_login,
                    cfg.nowpayments_password.get_secret_value(),
                )
            )
        if config.common.test_payments:
            gateways.append(TestGateway())
        try:
            yield PaymentGateways({g.code: g for g in gateways})
        finally:
            if cryptopay is not None:
                await cryptopay.close()
