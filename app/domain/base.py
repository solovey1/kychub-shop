from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import BigInteger, DateTime, Enum, Integer, Numeric, SmallInteger, String
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import DeclarativeBase, registry

from app.domain.enums.broadcast import BroadcastStatus
from app.domain.enums.catalog import AssignMode
from app.domain.enums.dispute import DisputeResolution
from app.domain.enums.ledger import LedgerAccount, LedgerKind, PaymentStatus, WithdrawalStatus
from app.domain.enums.order import OrderStatus
from app.domain.enums.support import ChatRole, ConversationKind, TicketStatus
from app.utils.custom_types import DictStrAny, Int16, Int32, Int64, Money


def _str_enum(cls: type[StrEnum]) -> Enum:
    # VARCHAR, not a native PG enum: adding a value later needs no ALTER TYPE
    # create_constraint: a CHECK named ck_<enum> keeps stray values out
    return Enum(
        cls,
        native_enum=False,
        length=32,
        create_constraint=True,
        name=f"ck_{cls.__name__.lower()}",
        values_callable=lambda e: [m.value for m in e],
    )


class Base(DeclarativeBase):
    registry = registry(
        type_annotation_map={
            Int16: SmallInteger(),
            Int32: Integer(),
            Int64: BigInteger(),
            Money: Numeric(18, 2),
            Decimal: Numeric(18, 2),
            DictStrAny: JSONB(),
            list[str]: ARRAY(String()),
            list[int]: ARRAY(BigInteger()),
            datetime: DateTime(timezone=True),
            **{
                cls: _str_enum(cls)
                for cls in (
                    AssignMode,
                    LedgerAccount,
                    LedgerKind,
                    PaymentStatus,
                    WithdrawalStatus,
                    OrderStatus,
                    ConversationKind,
                    TicketStatus,
                    ChatRole,
                    BroadcastStatus,
                    DisputeResolution,
                )
            },
        }
    )
