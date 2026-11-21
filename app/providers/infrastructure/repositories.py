from dishka import Provider, Scope, alias, provide, provide_all

from app.application.ports.repositories.balance import BalanceGateway
from app.application.ports.repositories.catalog import CatalogGateway
from app.application.ports.repositories.ledger import LedgerGateway
from app.application.ports.repositories.orders import OrdersGateway
from app.application.ports.repositories.promo import PromoGateway
from app.application.ports.repositories.stock import StockGateway
from app.application.ports.repositories.users import UsersGateway
from app.application.ports.uow import UnitOfWork
from app.infrastructure.postgres.repositories.balance import BalanceRepository
from app.infrastructure.postgres.repositories.catalog import CatalogRepository
from app.infrastructure.postgres.repositories.ledger import LedgerRepository
from app.infrastructure.postgres.repositories.orders import OrdersRepository
from app.infrastructure.postgres.repositories.promo import PromoRepository
from app.infrastructure.postgres.repositories.stock import StockRepository
from app.infrastructure.postgres.repositories.users import UsersRepository
from app.infrastructure.postgres.repository_helper import SqlRepositoryHelper
from app.infrastructure.postgres.uow import UoW


class RepositoriesProvider(Provider):
    scope = Scope.REQUEST

    database = provide_all(
        UoW,
        SqlRepositoryHelper,
        provide(UsersRepository, provides=UsersGateway),
        provide(LedgerRepository, provides=LedgerGateway),
        provide(CatalogRepository, provides=CatalogGateway),
        provide(OrdersRepository, provides=OrdersGateway),
        provide(StockRepository, provides=StockGateway),
        provide(PromoRepository, provides=PromoGateway),
        provide(BalanceRepository, provides=BalanceGateway),
        alias(source=UoW, provides=UnitOfWork),
    )
