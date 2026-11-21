import asyncio
import logging
from collections.abc import Callable, Iterable
from typing import Any, Final, Protocol

from app.domain.support import Message

logger: Final = logging.getLogger(__name__)

SEND_TIMEOUT: Final = 5


class Sink(Protocol):
    async def send_json(self, data: Any) -> None: ...


class EventHub:
    """Live events for the Mini App: user id -> that user's open sockets.

    ponytail: lives in one process; with several replicas an event reaches only the sockets of
    the replica that produced it. Replace with Redis pub/sub when the app is scaled out."""

    def __init__(self) -> None:
        self._sinks: dict[int, set[Sink]] = {}

    def connect(self, user_id: int, sink: Sink) -> None:
        self._sinks.setdefault(user_id, set()).add(sink)

    def disconnect(self, user_id: int, sink: Sink) -> None:
        sinks = self._sinks.get(user_id)
        if sinks is not None:
            sinks.discard(sink)
            if not sinks:
                del self._sinks[user_id]

    async def publish(self, user_ids: Iterable[int], event: dict[str, Any]) -> None:
        """The same event to every socket of these users; a dead socket is dropped."""
        for user_id in set(user_ids):
            for sink in list(self._sinks.get(user_id, ())):
                await self._send(user_id, sink, event)

    async def publish_each(
        self, user_ids: Iterable[int], build: Callable[[int], dict[str, Any]]
    ) -> None:
        """An event made for each user separately."""
        for user_id in set(user_ids):
            await self.publish([user_id], build(user_id))

    async def _send(self, user_id: int, sink: Sink, event: dict[str, Any]) -> None:
        try:
            await asyncio.wait_for(sink.send_json(event), SEND_TIMEOUT)
        except Exception:
            logger.info("dropping a dead socket of user %s", user_id)
            self.disconnect(user_id, sink)


def message_view(message: Message, user_id: int) -> dict[str, Any]:
    """A message as `user_id` may see it: the sender is a role, never an id or a name."""
    return {
        "id": message.id,
        "sender_role": message.sender_role.value,
        "mine": message.sender_id == user_id,
        "text": message.text,
        "media_type": (message.media or {}).get("type"),
        "created_at": message.created_at.isoformat(),
    }
