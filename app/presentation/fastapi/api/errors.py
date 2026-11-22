from typing import Final

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.application.errors.base import AppError, InsufficientFunds, UserNotFound
from app.application.errors.shop import (
    AliasTaken,
    ChatForbidden,
    Conflict,
    ExecutorExists,
    ExecutorNotFound,
    InvalidAmount,
    InvalidField,
    InvalidInput,
    ManagerExists,
    ManagerNotFound,
    NotFound,
    OrderUnavailable,
    PaymentNotFound,
    PromoError,
    TicketUnavailable,
    UnknownCountry,
    UnknownService,
)

NOT_FOUND: Final = (
    OrderUnavailable,
    TicketUnavailable,
    ChatForbidden,
    ExecutorNotFound,
    ManagerNotFound,
    PaymentNotFound,
    UserNotFound,
    NotFound,
)
CONFLICT: Final = (Conflict, AliasTaken, ExecutorExists, ManagerExists)
UNPROCESSABLE: Final = (
    InsufficientFunds,
    InvalidAmount,
    InvalidInput,
    PromoError,
    UnknownCountry,
    UnknownService,
)


def _code(error: AppError) -> str:
    return error.code if isinstance(error, (PromoError, Conflict)) else type(error).__name__


async def app_error_handler(_: Request, error: Exception) -> JSONResponse:
    assert isinstance(error, AppError)
    status = (
        404
        if isinstance(error, NOT_FOUND)
        else 409
        if isinstance(error, CONFLICT)
        else 422
        if isinstance(error, UNPROCESSABLE)
        else 400
    )
    body = {"code": _code(error), "detail": str(error)}
    if isinstance(error, InvalidField):
        body["field"] = error.field
    return JSONResponse(body, status_code=status)


def setup_errors(app: FastAPI) -> None:
    app.add_exception_handler(AppError, app_error_handler)
