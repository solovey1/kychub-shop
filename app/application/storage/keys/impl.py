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


@dataclass(kw_only=True, frozen=True)
class ActiveConversationKey(StorageKey[int], prefix="chat_active", type=int):
    """Значение — id текущей переписки пользователя (куда уходят его сообщения)."""

    user_id: int


@dataclass(kw_only=True, frozen=True)
class ChatHintKey(StorageKey[int], prefix="chat_hint", type=int):
    """Флаг: подсказка «как написать» уже показана этому пользователю в последний час."""

    user_id: int


@dataclass(kw_only=True, frozen=True)
class TicketOfferKey(StorageKey[list[list[int]]], prefix="ticket_offer", type=list[list[int]]):
    """Значение — пары [chat_id, message_id] уведомлений менеджерам о новом тикете."""

    ticket_id: int
