import logging
from dataclasses import dataclass
from typing import Final

from app.application.interactors.base import BaseInteractor
from app.application.interactors.ledger import LedgerService
from app.application.interactors.payouts import order_ref
from app.application.ports.repositories.ledger import LedgerGateway
from app.application.ports.repositories.orders import OrdersGateway
from app.application.ports.uow import UnitOfWork
from app.domain.enums.ledger import LedgerAccount, LedgerKind
from app.domain.enums.order import OrderStatus
from app.utils.time import datetime_now

logger: Final = logging.getLogger(__name__)


@dataclass(frozen=True)
class HoldInteractor(BaseInteractor):
    uow: UnitOfWork
    orders: OrdersGateway
    ledger: LedgerService
    ledger_gateway: LedgerGateway

    async def release_due(self) -> list[int]:
        """Moves earnings whose hold is over to the available balance. Each order has its own
        transaction, so one failure leaves the others alone."""
        released: list[int] = []
        for order_id in await self.orders.hold_due_ids(datetime_now()):
            try:
                if await self._release(order_id):
                    released.append(order_id)
            except Exception:
                await self.uow.rollback()
                logger.exception("releasing the hold of order %s failed", order_id)
        return released

    async def _release(self, order_id: int) -> bool:
        # the order lock serialises this with refunds and with a repeated run of the job
        order = await self.orders.get_for_update(order_id)
        if (
            order is None
            or order.status is not OrderStatus.completed
            or order.executor_id is None
            or order.hold_until is None
            or order.hold_until > datetime_now()
        ):
            await self.uow.rollback()
            return False
        ref = order_ref(order)
        hold = LedgerAccount.executor_hold
        earning = await self.ledger_gateway.get_by_ref(
            order.executor_id, hold, LedgerKind.executor_earning, ref
        )
        done = await self.ledger_gateway.get_by_ref(
            order.executor_id, hold, LedgerKind.hold_release, ref
        )
        if earning is None or done is not None:
            await self.uow.rollback()
            return False
        for account, amount in (
            (hold, -earning.amount),
            (LedgerAccount.executor_available, earning.amount),
        ):
            await self.ledger.post(
                order.executor_id,
                account,
                amount,
                LedgerKind.hold_release,
                order_id=order.id,
                ref=ref,
            )
        order.hold_until = None  # out of the partial index once released
        await self.uow.commit()
        return True
