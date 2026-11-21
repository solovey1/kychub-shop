from dishka import Provider, Scope, provide_all

from app.application.interactors.balance import BalanceInteractor
from app.application.interactors.catalog import CatalogInteractor
from app.application.interactors.ledger import LedgerService
from app.application.interactors.orders import OrdersInteractor
from app.application.interactors.pm.user_status import PMInteractor
from app.application.interactors.promo import PromoService
from app.application.interactors.purchase import PurchaseInteractor


class InteractorsProvider(Provider):
    scope = Scope.REQUEST

    interactors = provide_all(
        PMInteractor,
        LedgerService,
        CatalogInteractor,
        PromoService,
        PurchaseInteractor,
        OrdersInteractor,
        BalanceInteractor,
    )
