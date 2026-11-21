from typing import Final

from aiogram import Router

from . import catalog, inline, menu, purchase

router: Final[Router] = Router(name=__name__)
router.include_routers(menu.router, catalog.router, inline.router, purchase.router)
