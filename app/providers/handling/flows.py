from dishka import Provider, Scope, provide_all

from app.presentation.telegram.flows.common.balance import BalanceFlow
from app.presentation.telegram.flows.common.catalog import CatalogFlow
from app.presentation.telegram.flows.common.feedback import FeedbackFlow
from app.presentation.telegram.flows.common.managers import ManagerAdminFlow
from app.presentation.telegram.flows.common.menu import CommonMenuFlow
from app.presentation.telegram.flows.common.orders import OrdersFlow
from app.presentation.telegram.flows.common.purchase import PurchaseFlow
from app.presentation.telegram.flows.executor.admin import ExecutorAdminFlow
from app.presentation.telegram.flows.executor.cabinet import CabinetFlow
from app.presentation.telegram.flows.executor.orders import ExecutorOrdersFlow
from app.presentation.telegram.flows.executor.review import ReviewFlow
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
        ExecutorAdminFlow,
        CabinetFlow,
        ExecutorOrdersFlow,
        ReviewFlow,
        FeedbackFlow,
        ManagerAdminFlow,
    )
