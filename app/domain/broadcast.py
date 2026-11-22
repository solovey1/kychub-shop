from datetime import datetime
from typing import Optional

from sqlalchemy import CheckConstraint, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.enums.broadcast import BroadcastStatus
from app.utils.custom_types import DictStrAny, Int64

from .base import Base
from .mixins.timestamp import NowFunc


class Broadcast(Base):
    __tablename__ = "broadcasts"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_by: Mapped[Optional[Int64]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    text: Mapped[str] = mapped_column()
    media: Mapped[Optional[DictStrAny]] = mapped_column()
    status: Mapped[BroadcastStatus] = mapped_column(
        default=BroadcastStatus.draft, server_default=BroadcastStatus.draft.value
    )
    sent_count: Mapped[int] = mapped_column(default=0, server_default="0")
    failed_count: Mapped[int] = mapped_column(default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(server_default=NowFunc)
    started_at: Mapped[Optional[datetime]] = mapped_column()
    finished_at: Mapped[Optional[datetime]] = mapped_column()
    total_count: Mapped[Optional[int]] = mapped_column()  # recipients when it was started
    # the sender walks users by id: after a restart it goes on from here
    cursor_user_id: Mapped[Int64] = mapped_column(default=0, server_default="0")

    __table_args__ = (
        CheckConstraint("char_length(text) BETWEEN 1 AND 4096", name="broadcast_text_length"),
    )
