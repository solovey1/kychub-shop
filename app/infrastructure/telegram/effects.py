import logging
from dataclasses import dataclass
from typing import Final

from app.infrastructure.telegram.offers import OfferService

logger: Final = logging.getLogger(__name__)


@dataclass(frozen=True)
class Effects:
    """What happens in Telegram after an action succeeded. The bot flows and the Mini App API
    both call these, so a button and an endpoint always do the same. Call after the commit;
    a failure here is logged and never undoes the action."""

    offers: OfferService

    async def order_cancelled(self, order_id: int) -> None:
        try:
            await self.offers.close(order_id, "messages-executor-offer_cancelled")
        except Exception:
            logger.exception("closing the offers of order %s failed", order_id)
