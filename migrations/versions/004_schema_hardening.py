"""schema hardening: constraints, FKs, indexes, defaults, types

Revision ID: 004
Revises: 003
Create Date: 2026-11-21 20:00:00.000000

"""

from typing import Optional, Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "004"
down_revision: Optional[str] = "003"
branch_labels: Optional[Sequence[str]] = None
depends_on: Optional[Sequence[str]] = None

# (table, constraint name, expression)
CHECKS: list[tuple[str, str, str]] = [
    (
        "ledger_entries",
        "ledger_balance_non_negative",
        "account = 'executor_hold' OR balance_after >= 0",
    ),
    ("payments", "payment_amount_positive", "amount > 0"),
    ("promo_codes", "promo_discount_percent_range", "discount_percent BETWEEN 1 AND 100"),
    ("promo_codes", "promo_discount_amount_positive", "discount_amount > 0"),
    ("promo_codes", "promo_bonus_amount_positive", "bonus_amount > 0"),
    ("promo_codes", "promo_min_amount_non_negative", "min_amount >= 0"),
    ("promo_codes", "promo_usage_limit_positive", "usage_limit > 0"),
    ("promo_codes", "promo_code_upper", "code = upper(code)"),
    ("executor_profiles", "executor_parallel_positive", "max_parallel_orders >= 1"),
    ("stock_units", "stock_unlimited_never_sold", "NOT is_unlimited OR sold_order_id IS NULL"),
    (
        "conversations",
        "conversation_kind_target",
        "(kind = 'order' AND order_id IS NOT NULL AND ticket_id IS NULL)"
        " OR (kind = 'ticket' AND ticket_id IS NOT NULL AND order_id IS NULL)",
    ),
    (
        "orders",
        "order_assigned_has_executor",
        "status NOT IN ('assigned', 'ready') OR executor_id IS NOT NULL",
    ),
]

# (table, column, enum check name, values): VARCHAR enums get a CHECK
ENUMS: list[tuple[str, str, str, tuple[str, ...]]] = [
    ("services", "assign_mode", "ck_assignmode", ("queue", "auto")),
    (
        "ledger_entries",
        "account",
        "ck_ledgeraccount",
        ("main", "executor_hold", "executor_available"),
    ),
    (
        "ledger_entries",
        "kind",
        "ck_ledgerkind",
        (
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
        ),
    ),
    (
        "payments",
        "status",
        "ck_paymentstatus",
        ("created", "pending", "partially_paid", "canceled", "success"),
    ),
    ("withdrawals", "status", "ck_withdrawalstatus", ("pending", "approved", "paid", "rejected")),
    (
        "orders",
        "status",
        "ck_orderstatus",
        (
            "awaiting_input",
            "paid",
            "in_queue",
            "assigned",
            "ready",
            "completed",
            "failed",
            "refunded",
            "cancelled",
        ),
    ),
    ("tickets", "status", "ck_ticketstatus", ("open", "taken", "closed")),
    ("conversations", "kind", "ck_conversationkind", ("ticket", "order")),
    ("messages", "sender_role", "ck_chatrole", ("buyer", "executor", "manager", "admin")),
    ("broadcasts", "status", "ck_broadcaststatus", ("draft", "sending", "sent", "failed")),
]

CREATED_AT = (
    "categories services users audit_log broadcasts executor_profiles payments products "
    "withdrawals product_variants promo_codes orders ledger_entries order_events order_reviews "
    "promo_code_usages tickets messages"
).split()
UPDATED_AT = (
    "categories services users executor_profiles payments products withdrawals "
    "product_variants promo_codes orders"
).split()

# (table, column, referred table, constraint, ondelete before this revision)
FKS = [
    ("ledger_entries", "order_id", "orders", "ledger_entries_order_id_fkey", "SET NULL"),
    (
        "promo_code_usages",
        "promo_code_id",
        "promo_codes",
        "promo_code_usages_promo_code_id_fkey",
        "CASCADE",
    ),
    ("orders", "promo_code_id", "promo_codes", "orders_promo_code_id_fkey", "SET NULL"),
    ("promo_codes", "product_id", "products", "promo_codes_product_id_fkey", "CASCADE"),
]


def _set_default(tables: list[str], column: str, default: str) -> None:
    for table in tables:
        op.alter_column(table, column, server_default=sa.text(default))


def upgrade() -> None:
    # users.id is a Telegram id: no sequence
    op.execute("ALTER TABLE users ALTER COLUMN id DROP DEFAULT")
    op.execute("DROP SEQUENCE users_id_seq")

    # now() instead of timezone('UTC', now()): the column is timestamptz already
    _set_default(CREATED_AT, "created_at", "now()")
    _set_default(UPDATED_AT, "updated_at", "now()")

    for table, column, referred, name, _old in FKS:
        op.drop_constraint(name, table, type_="foreignkey")
        op.create_foreign_key(name, table, referred, [column], ["id"], ondelete="RESTRICT")

    for table, name, expr in CHECKS:
        op.create_check_constraint(name, table, sa.text(expr))
    for table, column, name, values in ENUMS:
        quoted = ", ".join(f"'{v}'" for v in values)
        op.create_check_constraint(name, table, sa.text(f"{column} IN ({quoted})"))

    op.create_index(
        "uq_stock_sold_order",
        "stock_units",
        ["sold_order_id"],
        unique=True,
        postgresql_where=sa.text("sold_order_id IS NOT NULL"),
    )
    op.create_index(
        "ix_stock_units_free",
        "stock_units",
        ["variant_id", "id"],
        postgresql_where=sa.text("sold_order_id IS NULL AND NOT is_unlimited"),
    )
    # NULLS NOT DISTINCT needs PostgreSQL 15+
    op.execute(
        "CREATE UNIQUE INDEX uq_tickets_open ON tickets (user_id, order_id) NULLS NOT DISTINCT "
        "WHERE status IN ('open', 'taken')"
    )
    op.create_index(
        "ix_orders_hold_due",
        "orders",
        ["hold_until"],
        postgresql_where=sa.text("status = 'completed' AND hold_until IS NOT NULL"),
    )
    op.create_index(
        "ix_orders_review_due",
        "orders",
        ["review_due_at"],
        postgresql_where=sa.text("status = 'completed' AND review_due_at IS NOT NULL"),
    )
    op.create_index(
        "ix_order_events_type_executor",
        "order_events",
        ["type", sa.text("(payload->>'executor_id')")],
    )
    # uq_conversations_ticket already covers it
    op.drop_index(op.f("ix_conversations_ticket_id"), table_name="conversations")


def downgrade() -> None:
    op.create_index(
        op.f("ix_conversations_ticket_id"), "conversations", ["ticket_id"], unique=False
    )
    op.drop_index("ix_order_events_type_executor", table_name="order_events")
    op.drop_index("ix_orders_review_due", table_name="orders")
    op.drop_index("ix_orders_hold_due", table_name="orders")
    op.drop_index("uq_tickets_open", table_name="tickets")
    op.drop_index("ix_stock_units_free", table_name="stock_units")
    op.drop_index("uq_stock_sold_order", table_name="stock_units")

    for table, _column, name, _values in reversed(ENUMS):
        op.drop_constraint(name, table, type_="check")
    for table, name, _expr in reversed(CHECKS):
        op.drop_constraint(name, table, type_="check")

    for table, column, referred, name, old in reversed(FKS):
        op.drop_constraint(name, table, type_="foreignkey")
        op.create_foreign_key(name, table, referred, [column], ["id"], ondelete=old)

    _set_default(UPDATED_AT, "updated_at", "timezone('UTC', now())")
    _set_default(CREATED_AT, "created_at", "timezone('UTC', now())")

    op.execute("CREATE SEQUENCE users_id_seq OWNED BY users.id")
    op.execute(
        "SELECT setval('users_id_seq', COALESCE((SELECT max(id) FROM users), 0) + 1, false)"
    )
    op.execute("ALTER TABLE users ALTER COLUMN id SET DEFAULT nextval('users_id_seq')")
