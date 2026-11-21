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


class AliasTaken(AppError):  # noqa: N818
    pass


class ExecutorExists(AppError):  # noqa: N818
    pass


class ExecutorNotFound(AppError):  # noqa: N818
    pass


class UnknownService(AppError):  # noqa: N818
    pass


class UnknownCountry(AppError):  # noqa: N818
    pass


class OrderUnavailable(AppError):  # noqa: N818
    """No such order for this actor, or it is not in a state the action needs."""


class DeadlineExpired(AppError):  # noqa: N818
    pass


class AlreadyRated(AppError):  # noqa: N818
    pass


class WalletNotSet(AppError):  # noqa: N818
    pass


class BelowMinimum(AppError):  # noqa: N818
    """The available balance is smaller than the minimum withdrawal."""


class TicketUnavailable(AppError):  # noqa: N818
    """No such ticket, it is closed, or the actor may not do this with it."""


class ChatForbidden(AppError):  # noqa: N818
    """The user may not write to this conversation (any more)."""


class ManagerExists(AppError):  # noqa: N818
    pass


class ManagerNotFound(AppError):  # noqa: N818
    pass
