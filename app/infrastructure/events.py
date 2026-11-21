import asyncio
import logging
from collections.abc import Callable, Iterable
from typing import Any, Final, Protocol

from app.domain.support import Message

logger: Final = logging.getLogger(__name__)

SEND_TIMEOUT: Final = 5
MAX_SOCKETS: Final = 5
REPLACED_CLOSE: Final = 4409


class Sink(Protocol):
    async def send_json(self, data: Any) -> None: ...

    async def close(self, code: int = 1000) -> None: ...


class EventHub:
    """Live events for the Mini App: user id -> that user's open sockets (oldest first).

    ponytail: lives in one process; with several replicas an event reaches only the sockets of
    the replica that produced it. Replace with Redis pub/sub when the app is scaled out."""

    def __init__(self) -> None:
        self._sinks: dict[int, list[Sink]] = {}

    async def connect(self, user_id: int, sink: Sink) -> None:
        """At most MAX_SOCKETS per user: the oldest one is closed to make room."""
        sinks = self._sinks.setdefault(user_id, [])
        sinks.append(sink)
        while len(sinks) > MAX_SOCKETS:
            old = sinks.pop(0)
            try:
                await old.close(REPLACED_CLOSE)
            except Exception:
                logger.debug("closing a replaced socket of user %s failed", user_id)

    def disconnect(self, user_id: int, sink: Sink) -> None:
        sinks = self._sinks.get(user_id)
        if sinks is not None and sink in sinks:
            sinks.remove(sink)
        if not sinks:
            self._sinks.pop(user_id, None)

    async def publish(self, user_ids: Iterable[int], event: dict[str, Any]) -> None:
        """The same event to every socket of these users, all at once."""
        await self._fan_out((uid, sink, event) for uid in set(user_ids) for sink in self._of(uid))

    async def publish_each(
        self, user_ids: Iterable[int], build: Callable[[int], dict[str, Any]]
    ) -> None:
        """An event made for each user separately."""
        await self._fan_out(
            (uid, sink, build(uid)) for uid in set(user_ids) for sink in self._of(uid)
        )

    def online(self, user_id: int) -> bool:
        return bool(self._sinks.get(user_id))

    def _of(self, user_id: int) -> list[Sink]:
        return list(self._sinks.get(user_id, ()))

    async def _fan_out(self, jobs: Iterable[tuple[int, Sink, dict[str, Any]]]) -> None:
        await asyncio.gather(*(self._send(uid, sink, event) for uid, sink, event in jobs))

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
