from dataclasses import dataclass
from typing import Any

from app.application.interactors.catalog import CatalogInteractor
from app.domain.user import User
from app.presentation.telegram.flows.base import BaseFlow
from app.presentation.telegram.presenters.common.catalog import CatalogPresenter
from app.presentation.telegram.view.renderer import Renderer


@dataclass(frozen=True)
class CatalogFlow(BaseFlow):
    user: User
    interactor: CatalogInteractor
    presenter: CatalogPresenter
    renderer: Renderer

    async def category(self, category_id: int, page: int) -> Any:
        data = await self.interactor.category(category_id, page)
        if data is None:
            return await self.renderer.apply(self.presenter.unavailable())
        return await self.renderer.apply(self.presenter.category(data))

    async def product(self, product_id: int) -> Any:
        card = await self.interactor.product(product_id)
        if card is None:
            return await self.renderer.apply(self.presenter.unavailable())
        return await self.renderer.apply(self.presenter.product(card))
