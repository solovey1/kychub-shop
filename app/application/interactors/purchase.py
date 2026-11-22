import re
from dataclasses import dataclass
from decimal import Decimal

from app.application.errors.shop import InvalidInput, OutOfStock, ProductUnavailable, PromoError
from app.application.fulfillment import FulfillmentRegistry
from app.application.interactors.base import BaseInteractor
from app.application.interactors.ledger import LedgerService
from app.application.interactors.payouts import order_ref
from app.application.interactors.promo import PromoService, discount_for
from app.application.models.form_schema import FieldType, FormSchema
from app.application.ports.repositories.catalog import CatalogGateway
from app.application.ports.repositories.executors import ExecutorsGateway
from app.application.ports.repositories.ledger import LedgerGateway
from app.application.ports.repositories.orders import OrdersGateway
from app.application.ports.repositories.promo import PromoGateway
from app.application.ports.uow import UnitOfWork
from app.domain.catalog import Country, Product, ProductVariant
from app.domain.enums.ledger import LedgerAccount, LedgerKind
from app.domain.enums.order import OrderStatus
from app.domain.order import Order, OrderEvent
from app.domain.promo import PromoCodeUsage


@dataclass(frozen=True)
class Quote:
    price: Decimal
    discount: Decimal
    total: Decimal
    balance: Decimal
    promo_code_id: int | None = None
    promo_error: str | None = None


ACCOUNT_SETS = 3  # answer sets offered to the buyer
ACCOUNT_SCAN = 20  # orders looked through to find them
LABEL_LIMIT = 24
_SECRET_KEY = re.compile(r"pass|pwd|password|secret|token|cookie|code|otp|2fa", re.I)
_LABEL_TYPES = (FieldType.login, FieldType.email, FieldType.text)


@dataclass(frozen=True)
class AnswerSet:
    """Answers of an earlier order. `label` is None when no field can name the account."""

    answers: dict[str, str]
    label: str | None
    code: str
    date: str  # DD.MM


def valid_answers(form: FormSchema, raw: dict[str, str]) -> dict[str, str]:
    """What of the old answers still fits the current form. Files never carry over."""
    found: dict[str, str] = {}
    for field in form.fields:
        if field.type is FieldType.file or not raw.get(field.key):
            continue
        try:
            found[field.key] = field.validate_value(raw[field.key])
        except ValueError:
            continue
    return found


@dataclass(frozen=True)
class Prepared:
    variant: ProductVariant
    product: Product
    country: Country | None
    form: FormSchema


@dataclass(frozen=True)
class PurchaseInteractor(BaseInteractor):
    uow: UnitOfWork
    catalog: CatalogGateway
    orders: OrdersGateway
    ledger: LedgerService
    ledger_gateway: LedgerGateway
    promo: PromoService
    promo_gateway: PromoGateway
    registry: FulfillmentRegistry
    executors: ExecutorsGateway

    async def _load(self, variant_id: int) -> tuple[ProductVariant, Product]:
        variant = await self.catalog.variant(variant_id)
        if variant is None or not variant.is_active:
            raise ProductUnavailable(f"variant {variant_id}")
        product = await self.catalog.product(variant.product_id)
        if product is None or not product.is_active:
            raise ProductUnavailable(f"product {variant.product_id}")
        return variant, product

    async def prepare(self, variant_id: int) -> Prepared:
        """Everything the buyer flow needs before asking questions. Raises OutOfStock early."""
        variant, product = await self._load(variant_id)
        if product.fulfillment_type == "stock":
            stock = await self.catalog.available_stock([variant.id])
            if not stock.get(variant.id):
                raise OutOfStock(f"variant {variant.id}")
        country = None
        if variant.country_code:
            country = (await self.catalog.countries([variant.country_code])).get(
                variant.country_code
            )
        form = FormSchema.model_validate(product.input_schema or {"fields": []})
        return Prepared(variant, product, country, form)

    async def online_executors(self, prep: Prepared) -> int | None:
        """How many executors are online for this product (busy ones too). None: the product is
        not done by executors."""
        product = prep.product
        if product.fulfillment_type != "executor" or product.service_id is None:
            return None
        found = await self.executors.candidates(
            product.service_id, prep.variant.country_code, set(), ignore_load=True
        )
        return len(found)

    async def is_first_order(self, user_id: int) -> bool:
        return await self.orders.count_for_user(user_id) == 0

    async def answer_sets(self, user_id: int, prep: Prepared) -> list[AnswerSet]:
        """Distinct answer sets of earlier orders of this product, newest first."""
        found: list[AnswerSet] = []
        seen: set[tuple[tuple[str, str], ...]] = set()
        orders = await self.orders.recent_with_input(user_id, prep.product.id, ACCOUNT_SCAN)
        for order in orders:
            answers = valid_answers(prep.form, dict(order.input_data))
            key = tuple(sorted(answers.items()))
            if not answers or key in seen:
                continue
            seen.add(key)
            label = next(
                (
                    answers[f.key]
                    for f in prep.form.fields
                    if f.type in _LABEL_TYPES
                    and f.key in answers
                    and not _SECRET_KEY.search(f.key)
                ),
                None,
            )
            if label and len(label) > LABEL_LIMIT:
                label = label[: LABEL_LIMIT - 1] + "…"
            found.append(AnswerSet(answers, label, order.code, f"{order.created_at:%d.%m}"))
            if len(found) == ACCOUNT_SETS:
                break
        return found

    async def quote(self, user_id: int, variant_id: int, promo_code: str | None) -> Quote:
        """Price preview. Writes nothing."""
        variant, product = await self._load(variant_id)
        price = variant.price
        discount = Decimal("0.00")
        promo_id: int | None = None
        error: str | None = None
        if promo_code:
            try:
                promo = await self.promo.check(
                    user_id, promo_code, bonus=False, amount=price, product_id=product.id
                )
                discount = discount_for(promo, price)
                promo_id = promo.id
            except PromoError as e:
                error = e.code
        balance = await self.ledger_gateway.balance(user_id, LedgerAccount.main)
        return Quote(price, discount, price - discount, balance, promo_id, error)

    async def purchase(
        self,
        user_id: int,
        variant_id: int,
        input_data: dict[str, str],
        promo_code: str | None,
        purchase_token: str,
    ) -> Order:
        """One transaction: promo, order, ledger posting, fulfillment, a single commit."""
        try:
            order = await self._purchase(
                user_id, variant_id, input_data, promo_code, purchase_token
            )
            await self.uow.commit()
            return order
        except BaseException:
            await self.uow.rollback()
            raise

    async def _purchase(
        self,
        user_id: int,
        variant_id: int,
        input_data: dict[str, str],
        promo_code: str | None,
        token: str,
    ) -> Order:
        ref = f"purchase:{token}"
        # serialises everything this user does with money; makes the replay check race-free
        await self.ledger_gateway.lock_user(user_id)
        replay = await self.ledger_gateway.get_by_ref(
            user_id, LedgerAccount.main, LedgerKind.purchase, ref
        )
        if replay is not None and replay.order_id is not None:
            existing = await self.orders.get_for_user(user_id, replay.order_id)
            if existing is not None:
                return existing
        # zero-total orders have no ledger entry, the token is also kept on the order
        if (existing := await self.orders.find_by_token(user_id, token)) is not None:
            return existing

        variant, product = await self._load(variant_id)
        answers = self._validate_input(product, input_data)
        price = variant.price
        discount = Decimal("0.00")
        promo = None
        if promo_code:
            promo = await self.promo.check(
                user_id, promo_code, bonus=False, amount=price, product_id=product.id, lock=True
            )
            promo.times_used += 1
            discount = discount_for(promo, price)

        handler = self.registry.get(product.fulfillment_type)
        if handler is None:
            raise ProductUnavailable(f"fulfillment {product.fulfillment_type}")

        order = Order(
            user_id=user_id,
            variant_id=variant.id,
            snapshot={
                "product": product.title_i18n,
                "variant": {"title": variant.title_i18n, "country": variant.country_code},
                "price": str(price),
                "type": product.fulfillment_type,
                "token": token,
            },
            price=price,
            discount=discount,
            promo_code_id=promo.id if promo else None,
            input_data=answers,
            status=OrderStatus.paid,
        )
        await self.orders.add(order)
        await self.orders.add_event(
            OrderEvent(
                order_id=order.id,
                actor_id=user_id,
                type="paid",
                payload={"price": str(price), "discount": str(discount)},
            )
        )
        if promo is not None:
            await self.promo_gateway.add_usage(
                PromoCodeUsage(promo_code_id=promo.id, user_id=user_id, order_id=order.id)
            )
        total = price - discount
        if total > 0:
            await self.ledger.post(
                user_id,
                LedgerAccount.main,
                -total,
                LedgerKind.purchase,
                order_id=order.id,
                ref=ref,
            )
        await handler.on_paid(order, product)
        if total > 0 and order.status is not OrderStatus.completed:
            # an executor or manual order: the money stays reserved until it is done
            await self.ledger.post(
                user_id,
                LedgerAccount.buyer_hold,
                total,
                LedgerKind.order_hold,
                order_id=order.id,
                ref=order_ref(order),
            )
        return order

    @staticmethod
    def _validate_input(product: Product, input_data: dict[str, str]) -> dict[str, str]:
        schema = FormSchema.model_validate(product.input_schema or {"fields": []})
        result: dict[str, str] = {}
        for field in schema.fields:
            try:
                result[field.key] = field.validate_value(input_data.get(field.key, ""))
            except ValueError as e:
                raise InvalidInput(f"{field.key}: {e}") from e
        return result
