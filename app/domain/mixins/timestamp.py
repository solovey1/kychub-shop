from datetime import datetime
from typing import Any, Final

from sqlalchemy import Function, func
from sqlalchemy.orm import Mapped, mapped_column

NowFunc: Final[Function[Any]] = func.now()


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(server_default=NowFunc)
    updated_at: Mapped[datetime] = mapped_column(server_default=NowFunc, onupdate=NowFunc)
