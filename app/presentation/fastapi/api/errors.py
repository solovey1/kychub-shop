from typing import Final

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.application.errors.base import AppError, InsufficientFunds, UserNotFound
from app.application.errors.shop import (
    ChatForbidden,
    ExecutorNotFound,
    InvalidAmount,
    InvalidInput,
    ManagerNotFound,
    OrderUnavailable,
    PaymentNotFound,
    PromoError,
    TicketUnavailable,
)

NOT_FOUND: Final = (
    OrderUnavailable,
    TicketUnavailable,
    ChatForbidden,
    ExecutorNotFound,
    ManagerNotFound,
    PaymentNotFound,
    UserNotFound,
)
UNPROCESSABLE: Final = (InsufficientFunds, InvalidAmount, InvalidInput, PromoError)


def _code(error: AppError) -> str:
    return error.code if isinstance(error, PromoError) else type(error).__name__


async def app_error_handler(_: Request, error: Exception) -> JSONResponse:
    assert isinstance(error, AppError)
    status = (
        404 if isinstance(error, NOT_FOUND) else 422 if isinstance(error, UNPROCESSABLE) else 400
    )
    return JSONResponse({"code": _code(error), "detail": str(error)}, status_code=status)


def setup_errors(app: FastAPI) -> None:
    app.add_exception_handler(AppError, app_error_handler)
