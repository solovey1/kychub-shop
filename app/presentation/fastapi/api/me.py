from html import unescape

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter

from app.application.errors.shop import ExecutorNotFound
from app.application.interactors.balance import BalanceInteractor
from app.application.interactors.executor_wallet import ExecutorWalletInteractor
from app.domain.enums.roles import Role
from app.presentation.fastapi.api.auth import CurrentUser
from app.presentation.fastapi.api.schemas import MeOut, WalletOut, usd

router: APIRouter = APIRouter(tags=["me"])


@router.get("/me")
@inject
async def me(
    user: CurrentUser,
    balance: FromDishka[BalanceInteractor],
    wallet: FromDishka[ExecutorWalletInteractor],
) -> MeOut:
    executor: WalletOut | None = None
    if user.roles & Role.EXECUTOR:
        try:
            summary = await wallet.summary(user.id)
            executor = WalletOut(hold=usd(summary.hold), available=usd(summary.available))
        except ExecutorNotFound:  # the role without a profile: nothing to show
            pass
    return MeOut(
        id=user.id,
        name=unescape(user.name),  # stored html-escaped for the bot's messages
        language=user.language,
        roles=[role.name.lower() for role in Role if user.roles & role and role.name],
        balance=usd(await balance.balance(user.id)),
        executor=executor,
    )
