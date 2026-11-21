from dishka import Provider, Scope, provide, provide_all

from app.application.ports.repositories.catalog import CatalogGateway
from app.application.ports.repositories.ledger import LedgerGateway
from app.application.ports.repositories.users import UsersGateway
from app.infrastructure.postgres.repositories.catalog import CatalogRepository
from app.infrastructure.postgres.repositories.ledger import LedgerRepository
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
    )
