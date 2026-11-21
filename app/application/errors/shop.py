from app.application.errors.base import AppError


class OutOfStock(AppError):  # noqa: N818
    pass


class ProductUnavailable(AppError):  # noqa: N818
    pass


class InvalidInput(AppError):  # noqa: N818
    pass


class InvalidAmount(AppError):  # noqa: N818
    pass


class TopupDisabled(AppError):  # noqa: N818
    pass


class PromoError(AppError):
    """`code` is a stable key, mapped to localized text by the presenter."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class PaymentNotFound(AppError):  # noqa: N818
    pass


class GatewayUnavailable(AppError):  # noqa: N818
    """The payment provider failed or timed out while creating an invoice."""
