from html import unescape

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, HTTPException

from app.application.errors.shop import ExecutorNotFound
from app.application.i18n_text import valid_timezone
from app.application.interactors.balance import BalanceInteractor
from app.application.interactors.executor_wallet import ExecutorWalletInteractor
from app.application.ports.repositories.users import UsersGateway
from app.domain.enums.roles import Role
from app.presentation.fastapi.api.auth import CurrentUser
from app.presentation.fastapi.api.schemas import MeOut, TimezoneIn, WalletOut, usd

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
        timezone=user.timezone,
        roles=[role.name.lower() for role in Role if user.roles & role and role.name],
        balance=usd(await balance.balance(user.id)),
        hold=usd(await balance.held(user.id)),
        executor=executor,
    )


@router.put("/me/timezone")
@inject
async def set_timezone(
    body: TimezoneIn, user: CurrentUser, users: FromDishka[UsersGateway]
) -> dict[str, bool]:
    """The Mini App tells the browser's zone; garbage is a 422."""
    if not valid_timezone(body.timezone):
        raise HTTPException(422, "Unknown time zone")
    if user.timezone != body.timezone:
        user.timezone = body.timezone
        await users.save(user)
    return {"ok": True}
