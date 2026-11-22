from dataclasses import dataclass

from app.application.errors.shop import Conflict, InvalidField
from app.application.interactors.admin.base import AdminInteractor
from app.domain.broadcast import Broadcast
from app.domain.enums.broadcast import BroadcastStatus
from app.utils.time import datetime_now

TEXT_MAX = 4096
LIST_LIMIT = 50


def clean_text(text: str) -> str:
    text = text.strip()
    if not 1 <= len(text) <= TEXT_MAX:
        raise InvalidField("text", f"1 to {TEXT_MAX} characters")
    return text


@dataclass(frozen=True)
class BroadcastAdminInteractor(AdminInteractor):
    async def broadcasts(self) -> list[Broadcast]:
        return await self.db.broadcasts(LIST_LIMIT)

    async def broadcast(self, broadcast_id: int) -> Broadcast:
        return await self.need(Broadcast, broadcast_id, lock=False)

    async def recipients(self) -> int:
        return await self.db.recipients_count()

    async def create(self, actor: int, text: str) -> Broadcast:
        async with self.tx():
            broadcast = Broadcast(created_by=actor, text=clean_text(text))
            await self.db.add(broadcast)
            await self.db.audit(actor, "broadcast.create", f"broadcast:{broadcast.id}", {})
        return broadcast

    async def update(self, actor: int, broadcast_id: int, text: str) -> Broadcast:
        async with self.tx():
            broadcast = await self.need(Broadcast, broadcast_id)
            if broadcast.status is not BroadcastStatus.draft:
                raise Conflict("not_draft")
            broadcast.text = clean_text(text)
            await self.db.audit(actor, "broadcast.update", f"broadcast:{broadcast_id}", {})
        return broadcast

    async def start(self, actor: int, broadcast_id: int) -> Broadcast:
        """draft -> sending; the scheduler job does the sending."""
        async with self.tx():
            broadcast = await self.need(Broadcast, broadcast_id)
            if broadcast.status is not BroadcastStatus.draft:
                raise Conflict("not_draft")
            broadcast.status = BroadcastStatus.sending
            broadcast.started_at = datetime_now()
            broadcast.total_count = await self.db.recipients_count()
            await self.db.audit(
                actor,
                "broadcast.start",
                f"broadcast:{broadcast_id}",
                {"recipients": broadcast.total_count},
            )
        return broadcast

    async def stop(self, actor: int, broadcast_id: int) -> Broadcast:
        async with self.tx():
            broadcast = await self.need(Broadcast, broadcast_id)
            if broadcast.status is not BroadcastStatus.sending:
                raise Conflict("not_sending")
            broadcast.status = BroadcastStatus.stopped
            broadcast.finished_at = datetime_now()
            await self.db.audit(actor, "broadcast.stop", f"broadcast:{broadcast_id}", {})
        return broadcast
