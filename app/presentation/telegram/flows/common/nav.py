from dataclasses import dataclass
from datetime import timedelta
from typing import Final

from aiogram.types import Message

from app.application.ports.storages.key_value import KvStorage
from app.application.ports.telegram.messages_helper import MessageHelper
from app.application.storage.keys.impl import NavScreenKey
from app.domain.user import User
from app.presentation.telegram.flows.base import BaseFlow
from app.presentation.telegram.flows.common.balance import BalanceFlow
from app.presentation.telegram.flows.common.catalog import CatalogFlow
from app.presentation.telegram.flows.common.chat import ChatFlow
from app.presentation.telegram.flows.common.orders import OrdersFlow
from app.presentation.telegram.view.renderer import Renderer

# Telegram deletes a message only within 48 hours, so a longer memory is of no use
SCREEN_TTL: Final = timedelta(hours=48)


@dataclass(frozen=True)
class ScreenTracker(BaseFlow):
    """Remembers the one navigation screen of the user (the main card or a bottom-button
    section) so the next one can replace it. Notifications and receipts are never tracked."""

    user: User
    kv: KvStorage
    helper: MessageHelper

    async def drop(self) -> None:
        key = NavScreenKey(user_id=self.user.id)
        previous = await self.kv.get(key)
        if previous is not None:
            await self.kv.delete(key)
            await self.helper.delete(message_id=previous)  # a gone or too old message is fine

    async def track(self, message: Message | None) -> None:
        if message is not None:
            await self.kv.set(NavScreenKey(user_id=self.user.id), message.message_id, SCREEN_TTL)


@dataclass(frozen=True)
class NavFlow(BaseFlow):
    """Taps on the bottom keyboard: the section opens as a fresh message, in any FSM state."""

    helper: MessageHelper
    renderer: Renderer
    screens: ScreenTracker
    catalog: CatalogFlow
    orders: OrdersFlow
    balance: BalanceFlow
    chat: ChatFlow

    async def open(self, section: str) -> None:
        await self.helper.fsm.clear()
        await self.helper.delete()  # the tap itself
        await self.screens.drop()
        match section:
            case "catalog":
                await self.catalog.category(0, 0)
            case "orders":
                await self.orders.list(0)
            case "balance":
                await self.balance.show()
            case "support":
                await self.chat.support(None)
        await self.screens.track(self.renderer.last_sent)
