"""Bodies of the admin API. Money is a string, texts are `{ru, en, uk}` dicts (`ru` required)."""

from typing import Annotated, Any, Literal

from pydantic import Field

from app.application.models.base import PydanticModel
from app.domain.enums.roles import Role
from app.domain.user import User
from app.presentation.fastapi.api.auth import require_perm

I18n = dict[str, str]
Direction = Literal["up", "down"]

CatalogUser = Annotated[User, require_perm(Role.CAN_CATALOG)]
CatalogOrUsers = Annotated[User, require_perm(Role.CAN_CATALOG, Role.CAN_USERS)]
UsersUser = Annotated[User, require_perm(Role.CAN_USERS)]
FinanceUser = Annotated[User, require_perm(Role.CAN_FINANCE)]
BroadcastUser = Annotated[User, require_perm(Role.CAN_BROADCAST)]
SettingsUser = Annotated[User, require_perm()]  # admins and owners only


class IdOut(PydanticModel):
    id: int


class OkOut(PydanticModel):
    ok: bool = True


class MoveIn(PydanticModel):
    direction: Direction


# --- catalog
class CategoryIn(PydanticModel):
    parent_id: int | None = None
    title: I18n
    is_active: bool = True


class CategoryPatch(PydanticModel):
    parent_id: int | None = None
    title: I18n | None = None
    is_active: bool | None = None


class CategoryOut(PydanticModel):
    id: int
    parent_id: int | None
    title: I18n
    position: int
    is_active: bool
    children: int
    products: int


class ProductBrief(PydanticModel):
    id: int
    title: I18n
    is_active: bool
    fulfillment_type: str
    variants: int
    price_from: str | None


FulfillmentType = Literal["stock", "fixed", "manual", "executor"]


class ProductIn(PydanticModel):
    category_id: int
    service_id: int | None = None
    title: I18n
    description: I18n = Field(default_factory=dict)
    fulfillment_type: FulfillmentType
    fulfillment_config: dict[str, Any] = Field(default_factory=dict)
    input_schema: dict[str, Any] | None = None
    result_schema: dict[str, Any] | None = None
    is_active: bool = True


class ProductPatch(PydanticModel):
    category_id: int | None = None
    service_id: int | None = None
    title: I18n | None = None
    description: I18n | None = None
    fulfillment_type: FulfillmentType | None = None
    fulfillment_config: dict[str, Any] | None = None
    input_schema: dict[str, Any] | None = None
    result_schema: dict[str, Any] | None = None
    is_active: bool | None = None


class VariantIn(PydanticModel):
    country_code: str | None = None
    title: I18n | None = None
    price: str
    is_active: bool = True


class VariantPatch(PydanticModel):
    country_code: str | None = None
    title: I18n | None = None
    price: str | None = None
    is_active: bool | None = None


class VariantOut(PydanticModel):
    id: int
    country_code: str | None
    title: I18n | None
    price: str
    is_active: bool
    stock: int | None  # unsold units, only for a `stock` product


class ProductOut(PydanticModel):
    id: int
    category_id: int
    service_id: int | None
    title: I18n
    description: I18n
    input_schema: dict[str, Any]
    result_schema: dict[str, Any]
    fulfillment_type: str
    fulfillment_config: dict[str, Any]
    is_active: bool
    variants: list[VariantOut]
    used: str | None  # `has_orders` / `has_promo`: it can only be switched off


class StockUnitOut(PydanticModel):
    id: int
    payload: str


class StockOut(PydanticModel):
    free: int
    unlimited: str | None
    recent: list[StockUnitOut]


class StockIn(PydanticModel):
    text: str = Field(max_length=2_000_000)


class UnlimitedIn(PydanticModel):
    text: str | None = Field(default=None, max_length=20000)


class StockImportOut(PydanticModel):
    added: int
    duplicates: int


class ServiceIn(PydanticModel):
    code: str
    title: str
    deadline_minutes: int
    assign_mode: Literal["queue", "auto"] = "queue"
    executor_percent: int
    is_active: bool = True


class ServicePatch(PydanticModel):
    title: str | None = None
    deadline_minutes: int | None = None
    assign_mode: Literal["queue", "auto"] | None = None
    executor_percent: int | None = None
    is_active: bool | None = None


class ServiceOut(PydanticModel):
    id: int
    code: str
    title: str
    deadline_minutes: int
    assign_mode: str
    executor_percent: int
    is_active: bool


class CountryIn(PydanticModel):
    code: str
    title: I18n


class CountryPatch(PydanticModel):
    title: I18n


class CountryOut(PydanticModel):
    code: str
    title: I18n
