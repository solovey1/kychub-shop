from dishka import Provider, Scope, provide_all

from app.application.interactors.admin.broadcasts import BroadcastAdminInteractor
from app.application.interactors.admin.catalog import CatalogAdminInteractor
from app.application.interactors.admin.money import MoneyAdminInteractor
from app.application.interactors.admin.orders import OrdersAdminInteractor
from app.application.interactors.admin.people import PeopleAdminInteractor
from app.application.interactors.admin.promo import PromoAdminInteractor
from app.application.interactors.admin.system import (
    AuditAdminInteractor,
    SettingsAdminInteractor,
    StatsAdminInteractor,
)
from app.application.interactors.auto_confirm import AutoConfirmInteractor
from app.application.interactors.balance import BalanceInteractor
from app.application.interactors.cards import CardBuilder
from app.application.interactors.catalog import CatalogInteractor
from app.application.interactors.conversations import ConversationInteractor
from app.application.interactors.deadlines import ExtensionInteractor, ReminderInteractor
from app.application.interactors.dispatch import DispatchInteractor
from app.application.interactors.executor_wallet import ExecutorWalletInteractor
from app.application.interactors.executors import (
    ExecutorAdminInteractor,
    ExecutorCabinetInteractor,
)
from app.application.interactors.feedback import ReviewInteractor, TipInteractor
from app.application.interactors.fulfillment_work import FulfillmentWorkInteractor
from app.application.interactors.hold import HoldInteractor
from app.application.interactors.ledger import LedgerService
from app.application.interactors.managers import ManagerAdminInteractor
from app.application.interactors.order_review import OrderReviewInteractor
from app.application.interactors.orders import OrdersInteractor
from app.application.interactors.pm.user_status import PMInteractor
from app.application.interactors.promo import PromoService
from app.application.interactors.purchase import PurchaseInteractor
from app.application.interactors.stats import ExecutorStats
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
        ExtensionInteractor,
        ReminderInteractor,
        FulfillmentWorkInteractor,
        OrderReviewInteractor,
        AutoConfirmInteractor,
        HoldInteractor,
        ReviewInteractor,
        TipInteractor,
        ExecutorStats,
        ExecutorWalletInteractor,
        ManagerAdminInteractor,
        ConversationInteractor,
        CatalogAdminInteractor,
        PeopleAdminInteractor,
        OrdersAdminInteractor,
        MoneyAdminInteractor,
        PromoAdminInteractor,
        BroadcastAdminInteractor,
        StatsAdminInteractor,
        SettingsAdminInteractor,
        AuditAdminInteractor,
    )
