class AppError(Exception):
    pass


class UserNotFound(AppError):  # noqa: N818
    pass


class InsufficientFunds(AppError):  # noqa: N818
    pass
