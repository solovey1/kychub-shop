from typing import Final

from aiogram import Router

from . import balance, catalog, chat, executor, feedback, menu, nav, orders, purchase, relay

router: Final[Router] = Router(name=__name__)
router.include_routers(
    nav.router,
    menu.router,
    chat.router,
    catalog.router,
    purchase.router,
    orders.router,
    balance.router,
    executor.router,
    executor.review_router,
    feedback.router,
    relay.router,
)
