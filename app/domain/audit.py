from datetime import datetime
from typing import Optional

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.utils.custom_types import DictStrAny, Int64

from .base import Base
from .mixins.timestamp import NowFunc


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    actor_id: Mapped[Optional[Int64]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    action: Mapped[str] = mapped_column()
    target: Mapped[Optional[str]] = mapped_column()
    payload: Mapped[DictStrAny] = mapped_column(default=dict, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(server_default=NowFunc)
