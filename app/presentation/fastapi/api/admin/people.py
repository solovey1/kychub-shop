from html import unescape

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter

from app.application.interactors.admin.people import PeopleAdminInteractor
from app.application.interactors.balance import BalanceInteractor, parse_money
from app.application.interactors.executor_wallet import ExecutorWalletInteractor
from app.application.interactors.executors import ExecutorAdminInteractor
from app.application.interactors.managers import ManagerAdminInteractor
from app.application.interactors.stats import ExecutorStats
from app.domain.enums.roles import Role
from app.domain.user import User
from app.presentation.fastapi.api.admin.schemas import (
    AdjustIn,
    BalanceAfterOut,
    ExecutorDetailOut,
    ExecutorIn,
    ExecutorPatch,
    ExecutorRowOut,
    ExecutorWalletOut,
    FinanceUser,
    ManagerOut,
    OkOut,
    PermissionsIn,
    RolesIn,
    ServicePermissionOut,
    SettingsUser,
    TgIdIn,
    UserBrief,
    UserCardOut,
    UserOrder,
    UsersUser,
)
from app.presentation.fastapi.api.schemas import StatsOut, usd

router: APIRouter = APIRouter(tags=["admin-people"])
People = FromDishka[PeopleAdminInteractor]


def role_names(user: User) -> list[str]:
    return [role.name.lower() for role in Role if user.roles & role and role.name]


def brief(user: User) -> UserBrief:
    return UserBrief(
        id=user.id, name=unescape(user.name), language=user.language, roles=role_names(user)
    )


@router.get("/users")
@inject
async def users(q: str, _: UsersUser, people: People) -> list[UserBrief]:
    return [brief(u) for u in await people.search(q)]


@router.get("/users/{user_id}")
@inject
async def user_card(
    user_id: int, viewer: UsersUser, people: People, balance: FromDishka[BalanceInteractor]
) -> UserCardOut:
    card = await people.user(user_id)
    sees_money = bool(viewer.roles & (Role.OWNER | Role.ADMIN | Role.CAN_FINANCE))
    user = card.user
    return UserCardOut(
        **brief(user).model_dump(),
        created_at=user.created_at,
        blocked=user.blocked_at is not None,
        balance=usd(await balance.balance(user_id)) if sees_money else None,
        orders=[
            UserOrder(
                id=o.id,
                status=o.status.value,
                product=(o.snapshot.get("product") or {}).get("ru", ""),
                total=usd(o.price - o.discount),
                created_at=o.created_at,
            )
            for o in card.orders
        ],
    )


@router.put("/users/{user_id}/roles")
@inject
async def set_roles(user_id: int, body: RolesIn, admin: SettingsUser, people: People) -> UserBrief:
    return brief(await people.set_roles(admin.id, user_id, body.flags))


@router.post("/users/{user_id}/balance")
@inject
async def adjust_balance(
    user_id: int, body: AdjustIn, admin: FinanceUser, balance: FromDishka[BalanceInteractor]
) -> BalanceAfterOut:
    entry = await balance.admin_topup(
        admin.id, user_id, parse_money(body.amount), body.comment.strip(), body.token
    )
    return BalanceAfterOut(balance=usd(entry.balance_after))


# --- executors
@router.get("/executors")
@inject
async def executors(_: UsersUser, people: People) -> list[ExecutorRowOut]:
    return [
        ExecutorRowOut(
            id=r.profile.user_id,
            alias=r.profile.alias,
            is_active=r.profile.is_active,
            online=r.profile.is_online,
            in_work=r.in_work,
            completed=r.completed,
            avg_score=r.avg_score,
        )
        for r in await people.executor_rows()
    ]


@router.get("/executors/{user_id}")
@inject
async def executor(
    user_id: int,
    _: UsersUser,
    people: People,
    stats: FromDishka[ExecutorStats],
    wallet: FromDishka[ExecutorWalletInteractor],
) -> ExecutorDetailOut:
    detail = await people.executor(user_id)
    profile = detail.profile
    summary = await wallet.summary(user_id)
    return ExecutorDetailOut(
        id=user_id,
        alias=profile.alias,
        name=unescape(detail.name),
        is_active=profile.is_active,
        online=profile.is_online,
        max_parallel=profile.max_parallel_orders,
        percent_override=profile.percent_override,
        permissions=[
            ServicePermissionOut(service_id=sid, countries=codes)
            for sid, codes in detail.permissions.items()
        ],
        stats=StatsOut(**vars(await stats.stats(user_id))),
        wallet=ExecutorWalletOut(
            hold=usd(summary.hold), available=usd(summary.available), wallet=summary.wallet
        ),
    )


@router.post("/executors")
@inject
async def register_executor(
    body: ExecutorIn, admin: UsersUser, executors: FromDishka[ExecutorAdminInteractor]
) -> OkOut:
    await executors.register(admin.id, body.tg_id, body.alias)
    return OkOut()


@router.patch("/executors/{user_id}")
@inject
async def update_executor(
    user_id: int,
    body: ExecutorPatch,
    admin: UsersUser,
    people: People,
    executors: FromDishka[ExecutorAdminInteractor],
) -> OkOut:
    sent = body.model_fields_set
    profile = (await people.executor(user_id)).profile
    if body.alias is not None and body.alias.strip() != profile.alias:
        await executors.rename(
            admin.id, user_id, body.alias
        )  # first: a taken name changes nothing
    if body.is_active is not None and body.is_active != profile.is_active:
        await executors.set_active(admin.id, user_id, body.is_active)
    if sent & {"max_parallel", "percent_override"}:
        percent = body.percent_override if "percent_override" in sent else profile.percent_override
        await executors.set_limits(admin.id, user_id, body.max_parallel, percent)
    return OkOut()


@router.put("/executors/{user_id}/permissions")
@inject
async def set_permissions(
    user_id: int,
    body: PermissionsIn,
    admin: UsersUser,
    people: People,
    executors: FromDishka[ExecutorAdminInteractor],
) -> OkOut:
    service = await people.service_code(body.service_id)
    await executors.set_permissions(admin.id, user_id, service, body.countries)
    return OkOut()


# --- managers
@router.get("/managers")
@inject
async def managers(_: UsersUser, people: People) -> list[ManagerOut]:
    return [ManagerOut(**brief(u).model_dump()) for u in await people.managers()]


@router.post("/managers")
@inject
async def add_manager(
    body: TgIdIn, admin: SettingsUser, managers: FromDishka[ManagerAdminInteractor]
) -> OkOut:
    await managers.add(admin.id, body.tg_id)
    return OkOut()


@router.delete("/managers/{tg_id}")
@inject
async def remove_manager(
    tg_id: int, admin: SettingsUser, managers: FromDishka[ManagerAdminInteractor]
) -> OkOut:
    await managers.remove(admin.id, tg_id)
    return OkOut()
