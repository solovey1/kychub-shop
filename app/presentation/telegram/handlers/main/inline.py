from typing import Final

from aiogram import Router
from aiogram.types import InlineQuery
from dishka import FromDishka

from app.presentation.telegram.flows.common.catalog import CatalogFlow

router: Final[Router] = Router(name=__name__)


@router.inline_query()
async def search(query: InlineQuery, flow: FromDishka[CatalogFlow]) -> None:
    await flow.inline(query)
