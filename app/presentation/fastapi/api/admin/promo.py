from decimal import Decimal
from typing import Literal

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter

from app.application.interactors.admin.promo import PromoAdminInteractor
from app.application.ports.repositories.orders import OrdersGateway
from app.domain.promo import PromoCode
from app.presentation.fastapi.api.admin.schemas import (
    FinanceUser,
    IdOut,
    OkOut,
    PromoBrief,
    PromoIn,
    PromoOut,
    PromoPatch,
    PromoUsageOut,
)
from app.presentation.fastapi.api.schemas import usd

router: APIRouter = APIRouter(tags=["admin-promo"])
Promos = FromDishka[PromoAdminInteractor]


def _brief(p: PromoCode) -> PromoBrief:
    kind: Literal["percent", "amount", "bonus"]
    if p.discount_percent is not None:
        kind, value = "percent", str(p.discount_percent)
    elif p.discount_amount is not None:
        kind, value = "amount", usd(p.discount_amount)
    else:
        kind, value = "bonus", usd(p.bonus_amount or Decimal(0))
    return PromoBrief(
        id=p.id,
        code=p.code,
        kind=kind,
        value=value,
        times_used=p.times_used,
        usage_limit=p.usage_limit,
        expires_at=p.expires_at,
        active=p.active,
    )


@router.get("/promos")
@inject
async def promos(_: FinanceUser, promo: Promos) -> list[PromoBrief]:
    return [_brief(p) for p in await promo.promos()]


@router.get("/promos/{promo_id}")
@inject
async def get_promo(
    promo_id: int, _: FinanceUser, promo: Promos, orders: FromDishka[OrdersGateway]
) -> PromoOut:
    p, usages = await promo.promo(promo_id)
    return PromoOut(
        **_brief(p).model_dump(),
        discount_percent=p.discount_percent,
        discount_amount=None if p.discount_amount is None else usd(p.discount_amount),
        bonus_amount=None if p.bonus_amount is None else usd(p.bonus_amount),
        product_id=p.product_id,
        min_amount=None if p.min_amount is None else usd(p.min_amount),
        new_users_only=p.new_users_only,
        allowed_user_ids=list(p.allowed_user_ids),
        reusable=p.reusable,
        usages=[
            PromoUsageOut(
                user_id=u.usage.user_id,
                name=u.name,
                order_id=u.usage.order_id,
                order_code=await orders.code(u.usage.order_id) if u.usage.order_id else None,
                created_at=u.usage.created_at,
            )
            for u in usages
        ],
    )


@router.post("/promos")
@inject
async def create_promo(body: PromoIn, user: FinanceUser, promo: Promos) -> IdOut:
    created = await promo.create(user.id, body.code, body.model_dump(exclude={"code"}))
    return IdOut(id=created.id)


@router.patch("/promos/{promo_id}")
@inject
async def update_promo(promo_id: int, body: PromoPatch, user: FinanceUser, promo: Promos) -> OkOut:
    await promo.update(user.id, promo_id, body.model_dump(exclude_unset=True))
    return OkOut()
