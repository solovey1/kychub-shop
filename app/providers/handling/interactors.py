from dishka import Provider, Scope, provide_all

from app.application.interactors.balance import BalanceInteractor
from app.application.interactors.cards import CardBuilder
from app.application.interactors.catalog import CatalogInteractor
from app.application.interactors.dispatch import DispatchInteractor
from app.application.interactors.executors import (
    ExecutorAdminInteractor,
    ExecutorCabinetInteractor,
)
from app.application.interactors.fulfillment_work import FulfillmentWorkInteractor
from app.application.interactors.hold import HoldInteractor
from app.application.interactors.ledger import LedgerService
from app.application.interactors.order_review import OrderReviewInteractor
from app.application.interactors.orders import OrdersInteractor
from app.application.interactors.pm.user_status import PMInteractor
from app.application.interactors.promo import PromoService
from app.application.interactors.purchase import PurchaseInteractor
from app.application.interactors.topup import TopupInteractor


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
        TopupInteractor,
        ExecutorAdminInteractor,
        ExecutorCabinetInteractor,
        CardBuilder,
        DispatchInteractor,
        FulfillmentWorkInteractor,
        OrderReviewInteractor,
        HoldInteractor,
    )
