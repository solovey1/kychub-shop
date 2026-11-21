from typing import Final

from aiogram import Router

from . import balance, catalog, executor, inline, menu, orders, purchase

router: Final[Router] = Router(name=__name__)
router.include_routers(
    menu.router,
    catalog.router,
    inline.router,
    purchase.router,
    orders.router,
    balance.router,
    executor.router,
)
