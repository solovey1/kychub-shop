from typing import cast

from aiogram import html
from aiogram.types import CallbackQuery, ErrorEvent, Message, TelegramObject, Update
from aiogram.types import User as AiogramUser
from aiogram_i18n.cores import FluentRuntimeCore
from dishka import FromDishka, Provider, Scope, provide, provide_all
from dishka.integrations.aiogram import AiogramMiddlewareData, AiogramProvider

from app.application.models.config import AppConfig
from app.application.ports.repositories.users import UsersGateway
from app.application.ports.telegram.messages_helper import MessageHelper
from app.const import DEFAULT_LOCALE
from app.domain.enums.roles import Role
from app.domain.user import User
from app.infrastructure.telegram.effects import Effects
from app.infrastructure.telegram.notices import OrderNotices
from app.infrastructure.telegram.notifier import Notifier
from app.infrastructure.telegram.offers import OfferService
from app.infrastructure.telegram.relay import Relay
from app.infrastructure.telegram.ticket_offers import TicketOffers
from app.presentation.telegram.helpers.messages import MessageHelperImpl
from app.presentation.telegram.view.renderer import Renderer

OWNER_ROLES = (
    Role.OWNER
    | Role.ADMIN
    | Role.CAN_CATALOG
    | Role.CAN_FINANCE
    | Role.CAN_USERS
    | Role.CAN_BROADCAST
)


async def _ensure_owner(user: User, config: AppConfig, users_gateway: UsersGateway) -> User:
    is_owner = user.id in config.common.owner_id_set
    if is_owner and not user.roles & Role.OWNER:
        user.roles |= OWNER_ROLES
        await users_gateway.save(user)
    elif not is_owner and user.roles & Role.OWNER:
        user.roles &= ~OWNER_ROLES
        await users_gateway.save(user)
    return user


class UserProvider(AiogramProvider):
    @provide(scope=Scope.REQUEST)
    async def provide_user(
        self,
        middleware_data: AiogramMiddlewareData,
        users_gateway: FromDishka[UsersGateway],
        core: FromDishka[FluentRuntimeCore],
        config: FromDishka[AppConfig],
    ) -> User:
        aiogram_user: AiogramUser | None = middleware_data.get("event_from_user")
        if aiogram_user is None or aiogram_user.is_bot:
            raise RuntimeError("User cannot be resolved for this handler")

        user: User | None = await users_gateway.get(user_id=aiogram_user.id)
        if user is not None:
            if not user.name:  # placeholder made by an admin (executor registration)
                user.name = html.quote(aiogram_user.full_name)
                user.language_code = aiogram_user.language_code
                if aiogram_user.language_code in core.available_locales:
                    user.language = aiogram_user.language_code
                await users_gateway.save(user)
            return await _ensure_owner(user, config, users_gateway)

        language: str = (
            aiogram_user.language_code
            if aiogram_user.language_code and aiogram_user.language_code in core.available_locales
            else DEFAULT_LOCALE
        )
        user = await users_gateway.create(
            user_id=aiogram_user.id,
            name=html.quote(aiogram_user.full_name),
            language=language,
            language_code=aiogram_user.language_code,
        )
        return await _ensure_owner(user, config, users_gateway)


class MessageHelperProvider(AiogramProvider):
    @provide(scope=Scope.REQUEST)
    def provide_message_helper(
        self,
        event: TelegramObject,
        middleware_data: AiogramMiddlewareData,
    ) -> MessageHelper:
        update: TelegramObject = event
        if isinstance(update, ErrorEvent):
            update = update.update
        if isinstance(update, Update):
            update = update.event
        return MessageHelperImpl(
            update=cast(Message | CallbackQuery, update),
            bot=middleware_data["bot"],
            fsm_context=middleware_data.get("state"),
        )


class RequestInfrastructureProvider(Provider):
    scope = Scope.REQUEST

    infrastructure = provide_all(
        Renderer, Notifier, OfferService, OrderNotices, Relay, TicketOffers, Effects
    )
