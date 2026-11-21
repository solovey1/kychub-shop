from dishka import Provider, Scope, provide_all

from app.presentation.telegram.flows.common.balance import BalanceFlow
from app.presentation.telegram.flows.common.catalog import CatalogFlow
from app.presentation.telegram.flows.common.menu import CommonMenuFlow
from app.presentation.telegram.flows.common.orders import OrdersFlow
from app.presentation.telegram.flows.common.purchase import PurchaseFlow
from app.presentation.telegram.flows.extra.errors import ExtraErrorsFlow
from app.presentation.telegram.flows.extra.pm import PMFlow


class FlowsProvider(Provider):
    scope = Scope.REQUEST

    flows = provide_all(
        CommonMenuFlow,
        ExtraErrorsFlow,
        PMFlow,
        CatalogFlow,
        PurchaseFlow,
        OrdersFlow,
        BalanceFlow,
    )
