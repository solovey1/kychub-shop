from html import unescape
from typing import Literal

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter

from app.application.interactors.admin.money import MoneyAdminInteractor
from app.domain.enums.ledger import WithdrawalStatus
from app.infrastructure.telegram.effects import Effects
from app.presentation.fastapi.api.admin.schemas import (
    DecidedOut,
    FinanceUser,
    PayIn,
    RejectIn,
    WithdrawalOut,
)
from app.presentation.fastapi.api.schemas import usd

router: APIRouter = APIRouter(tags=["admin-money"])
Money = FromDishka[MoneyAdminInteractor]


@router.get("/withdrawals")
@inject
async def withdrawals(
    _: FinanceUser,
    money: Money,
    status: Literal["pending", "paid", "rejected"] = "pending",
) -> list[WithdrawalOut]:
    return [
        WithdrawalOut(
            id=r.withdrawal.id,
            executor_id=r.withdrawal.executor_id,
            alias=r.alias,
            name=unescape(r.name),
            amount=usd(r.withdrawal.amount),
            address=r.withdrawal.address,
            status=r.withdrawal.status.value,
            tx_hash=r.withdrawal.tx_hash,
            reject_reason=r.withdrawal.reject_reason,
            created_at=r.withdrawal.created_at,
            processed_at=r.withdrawal.processed_at,
        )
        for r in await money.withdrawals(WithdrawalStatus(status))
    ]


@router.post("/withdrawals/{withdrawal_id}/pay")
@inject
async def pay(
    withdrawal_id: int, body: PayIn, user: FinanceUser, money: Money, effects: FromDishka[Effects]
) -> DecidedOut:
    result = await money.pay(user.id, withdrawal_id, body.tx_hash)
    if result.changed:
        await effects.withdrawal_paid(result.withdrawal)
    return DecidedOut(changed=result.changed)


@router.post("/withdrawals/{withdrawal_id}/reject")
@inject
async def reject(
    withdrawal_id: int,
    body: RejectIn,
    user: FinanceUser,
    money: Money,
    effects: FromDishka[Effects],
) -> DecidedOut:
    result = await money.reject(user.id, withdrawal_id, body.reason)
    if result.changed:
        await effects.withdrawal_rejected(result.withdrawal)
    return DecidedOut(changed=result.changed)
