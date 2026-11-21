from datetime import timedelta
from typing import Annotated, Any, Final

from aiogram.utils.web_app import safe_parse_webapp_init_data
from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import Depends, Header, HTTPException, Request, status

from app.application.models.config import AppConfig
from app.application.ports.repositories.users import UsersGateway
from app.domain.enums.roles import Role
from app.domain.user import User
from app.utils.time import datetime_now

MAX_AGE: Final = timedelta(hours=24)
SCHEME: Final = "tma "


async def authenticate(init_data: str, config: AppConfig, users: UsersGateway) -> User | None:
    """The user behind a signed Mini App `initData`, or None: forged, older than 24 hours,
    or not in the database."""
    try:
        data = safe_parse_webapp_init_data(config.telegram.bot_token.get_secret_value(), init_data)
    except ValueError:
        return None
    if data.user is None or datetime_now() - data.auth_date > MAX_AGE:
        return None
    return await users.get(data.user.id)


def _unauthorized() -> HTTPException:
    return HTTPException(status.HTTP_401_UNAUTHORIZED, "Unauthorized")


@inject
async def current_user(
    request: Request,
    users: FromDishka[UsersGateway],
    config: FromDishka[AppConfig],
    authorization: Annotated[str | None, Header()] = None,
) -> User:
    """`Authorization: tma <initData>` on every request, no sessions."""
    if not authorization or not authorization.startswith(SCHEME):
        raise _unauthorized()
    user = await authenticate(authorization[len(SCHEME) :], config, users)
    if user is None:
        raise _unauthorized()
    return user


CurrentUser = Annotated[User, Depends(current_user)]


def require_role(*roles: Role) -> Any:
    wanted = Role(0)
    for role in roles:
        wanted |= role

    async def check(user: CurrentUser) -> User:
        if not user.roles & wanted:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Forbidden")
        return user

    return Depends(check)


ExecutorUser = Annotated[User, require_role(Role.EXECUTOR)]
StaffUser = Annotated[User, require_role(Role.MANAGER, Role.ADMIN)]
AdminUser = Annotated[User, require_role(Role.ADMIN)]
