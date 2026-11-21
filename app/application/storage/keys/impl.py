from dataclasses import dataclass

from app.application.storage.keys.base import StorageKey


@dataclass(kw_only=True, frozen=True)
class WebhookLockKey(StorageKey[str], prefix="webhook_lock", type=str):
    """Значение — хэш текущего установленного вебхука для этого bot_id."""

    bot_id: int


@dataclass(kw_only=True, frozen=True)
class CommandsLockKey(StorageKey[str], prefix="commands_lock", type=str):
    """Значение — хэш текущего набора команд бота для этого bot_id."""

    bot_id: int


@dataclass(kw_only=True, frozen=True)
class OrderOfferKey(StorageKey[list[list[int]]], prefix="order_offer", type=list[list[int]]):
    """Значение — пары [chat_id, message_id] отправленных исполнителям предложений заказа."""

    order_id: int
