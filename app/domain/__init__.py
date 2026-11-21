# Import every model so Base.metadata (Alembic autogenerate) sees all tables.
from . import (  # noqa: F401
    audit,
    broadcast,
    catalog,
    executor,
    ledger,
    order,
    promo,
    review,
    settings,
    support,
    user,
)
