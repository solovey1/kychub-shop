from decimal import Decimal
from typing import Literal

from pydantic import SecretStr

from .base import EnvSettings


class PaymentsConfig(EnvSettings, env_prefix="PAYMENTS_"):
    """A gateway is enabled only when all of its keys are set."""

    cryptopay_token: SecretStr | None = None
    cryptopay_network: Literal["mainnet", "testnet"] = "mainnet"

    binance_api_key: SecretStr | None = None
    binance_api_secret: SecretStr | None = None
    binance_pay_id: str | None = None  # shown to the buyer

    nowpayments_api_key: SecretStr | None = None
    nowpayments_login: str | None = None
    nowpayments_password: SecretStr | None = None

    min_topup: Decimal = Decimal(1)
    max_topup: Decimal = Decimal(10000)

    @property
    def cryptopay_enabled(self) -> bool:
        return bool(self.cryptopay_token)

    @property
    def binance_enabled(self) -> bool:
        return bool(self.binance_api_key and self.binance_api_secret and self.binance_pay_id)

    @property
    def nowpayments_enabled(self) -> bool:
        return bool(
            self.nowpayments_api_key and self.nowpayments_login and self.nowpayments_password
        )
