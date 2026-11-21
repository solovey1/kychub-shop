from dishka import Provider, Scope, provide_all

from app.presentation.telegram.presenters.common.catalog import CatalogPresenter
from app.presentation.telegram.presenters.common.menu import CommonMenuPresenter
from app.presentation.telegram.presenters.common.purchase import PurchasePresenter
from app.presentation.telegram.presenters.extra.errors import ExtraErrorsPresenter


class PresentersProvider(Provider):
    scope = Scope.REQUEST

    presenters = provide_all(
        CommonMenuPresenter, ExtraErrorsPresenter, CatalogPresenter, PurchasePresenter
    )
