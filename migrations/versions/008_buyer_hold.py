"""buyer funds held until the order is done

Revision ID: 008
Revises: 007
Create Date: 2026-11-22 22:00:00.000000

"""

from typing import Optional, Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "008"
down_revision: Optional[str] = "007"
branch_labels: Optional[Sequence[str]] = None
depends_on: Optional[Sequence[str]] = None

ACCOUNTS = ("main", "executor_hold", "executor_available")
KINDS = (
    "topup",
    "purchase",
    "refund",
    "executor_earning",
    "earning_reversal",
    "hold_release",
    "tip",
    "withdrawal",
    "promo_bonus",
    "admin_adjust",
)
NEW_ACCOUNTS = ("buyer_hold",)
NEW_KINDS = ("order_hold", "order_capture", "order_release")


def _swap(account_values: tuple[str, ...], kind_values: tuple[str, ...]) -> None:
    for column, name, values in (
        ("account", "ck_ledgeraccount", account_values),
        ("kind", "ck_ledgerkind", kind_values),
    ):
        quoted = ", ".join(f"'{v}'" for v in values)
        op.drop_constraint(name, "ledger_entries", type_="check")
        op.create_check_constraint(name, "ledger_entries", sa.text(f"{column} IN ({quoted})"))


def upgrade() -> None:
    _swap(ACCOUNTS + NEW_ACCOUNTS, KINDS + NEW_KINDS)


def downgrade() -> None:
    op.execute("DELETE FROM ledger_entries WHERE account = 'buyer_hold'")
    _swap(ACCOUNTS, KINDS)
