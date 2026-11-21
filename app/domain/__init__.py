# Import every model so Base.metadata (Alembic autogenerate) sees all tables.
from . import catalog, ledger, order, user  # noqa: F401
