from typing import Final

from app.domain.enums.roles import Role

from .magic_data import MagicData
from .roles import HasRole

ADMIN_FILTER: Final[HasRole] = HasRole(Role.ADMIN)

__all__ = ["ADMIN_FILTER", "HasRole", "MagicData"]
