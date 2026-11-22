# Import every model so Base.metadata (Alembic autogenerate) sees all tables.
from . import (  # noqa: F401
    audit,
    broadcast,
    catalog,
    dispute,
    executor,
    ledger,
    order,
    promo,
    review,
    settings,
    support,
    user,
)
