from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter

from app.application.i18n_text import pick_i18n
from app.application.interactors.admin.system import StatsAdminInteractor
from app.presentation.fastapi.api.admin.schemas import (
    FinanceUser,
    StatsDataOut,
    TopProductOut,
)
from app.presentation.fastapi.api.schemas import usd

router: APIRouter = APIRouter(tags=["admin-stats"])


@router.get("/stats")
@inject
async def stats(
    user: FinanceUser, interactor: FromDishka[StatsAdminInteractor], days: int = 7
) -> StatsDataOut:
    data = await interactor.stats(days)
    return StatsDataOut(
        days=days,
        revenue=usd(data.revenue),
        refunds=usd(data.refunds),
        topups=usd(data.topups),
        paid_out=usd(data.paid_out),
        orders=data.orders,
        top=[
            TopProductOut(
                product_id=t.product_id,
                title=pick_i18n(t.title, user.language),
                orders=t.orders,
                revenue=usd(t.revenue),
            )
            for t in data.top
        ],
        hold=usd(data.hold),
        available=usd(data.available),
        buyers=usd(data.buyers),
    )
