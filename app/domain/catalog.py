from typing import Optional

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, true
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.enums.catalog import AssignMode
from app.utils.custom_types import DictStrAny, Money

from .base import Base
from .mixins.timestamp import TimestampMixin


class Category(Base, TimestampMixin):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    parent_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("categories.id", ondelete="RESTRICT"), index=True
    )
    title_i18n: Mapped[DictStrAny] = mapped_column()
    position: Mapped[int] = mapped_column(default=0, server_default="0")
    is_active: Mapped[bool] = mapped_column(default=True, server_default=true())


class Service(Base, TimestampMixin):
    __tablename__ = "services"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True)
    title: Mapped[str] = mapped_column()
    deadline_minutes: Mapped[int] = mapped_column()
    assign_mode: Mapped[AssignMode] = mapped_column(default=AssignMode.queue)
    executor_percent: Mapped[int] = mapped_column()
    is_active: Mapped[bool] = mapped_column(default=True, server_default=true())

    __table_args__ = (
        CheckConstraint("executor_percent BETWEEN 0 AND 100", name="service_percent_range"),
    )


class Country(Base):
    __tablename__ = "countries"

    code: Mapped[str] = mapped_column(String(2), primary_key=True)
    title_i18n: Mapped[DictStrAny] = mapped_column()


class Product(Base, TimestampMixin):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id", ondelete="RESTRICT"))
    service_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("services.id", ondelete="RESTRICT")
    )
    title_i18n: Mapped[DictStrAny] = mapped_column()
    description_i18n: Mapped[DictStrAny] = mapped_column(default=dict, server_default="{}")
    input_schema: Mapped[DictStrAny] = mapped_column(default=dict, server_default="{}")
    result_schema: Mapped[DictStrAny] = mapped_column(default=dict, server_default="{}")
    fulfillment_type: Mapped[str] = mapped_column(String(32))
    fulfillment_config: Mapped[DictStrAny] = mapped_column(default=dict, server_default="{}")
    is_active: Mapped[bool] = mapped_column(default=True, server_default=true())
    position: Mapped[int] = mapped_column(default=0, server_default="0")

    __table_args__ = (Index("ix_products_category_id", "category_id"),)


class ProductVariant(Base, TimestampMixin):
    __tablename__ = "product_variants"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), index=True
    )
    country_code: Mapped[Optional[str]] = mapped_column(
        String(2), ForeignKey("countries.code", ondelete="RESTRICT")
    )
    title_i18n: Mapped[Optional[DictStrAny]] = mapped_column()
    price: Mapped[Money] = mapped_column()
    is_active: Mapped[bool] = mapped_column(default=True, server_default=true())

    __table_args__ = (CheckConstraint("price >= 0", name="variant_price_non_negative"),)


class StockUnit(Base):
    __tablename__ = "stock_units"

    id: Mapped[int] = mapped_column(primary_key=True)
    variant_id: Mapped[int] = mapped_column(ForeignKey("product_variants.id", ondelete="CASCADE"))
    payload: Mapped[str] = mapped_column()
    is_unlimited: Mapped[bool] = mapped_column(default=False, server_default="false")
    sold_order_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("orders.id", ondelete="SET NULL")
    )

    __table_args__ = (Index("ix_stock_units_variant_sold", "variant_id", "sold_order_id"),)
