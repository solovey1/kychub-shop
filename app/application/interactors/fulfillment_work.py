from dataclasses import dataclass

from app.application.cards import OrderCard
from app.application.errors.shop import DeadlineExpired, InvalidInput, OrderUnavailable
from app.application.fulfillment.base import move
from app.application.i18n_text import pick_i18n
from app.application.interactors.base import BaseInteractor
from app.application.interactors.cards import CardBuilder, load_context
from app.application.interactors.catalog import PAGE_SIZE
from app.application.models.form_schema import FieldType, FormField, FormSchema
from app.application.ports.repositories.catalog import CatalogGateway
from app.application.ports.repositories.orders import OrdersGateway
from app.application.ports.uow import UnitOfWork
from app.domain.enums.order import OrderStatus
from app.domain.order import Order, OrderEvent
from app.utils.time import datetime_now

DEFAULT_RESULT_FORM = FormSchema(
    fields=[
        FormField(
            key="result",
            label={"ru": "Результат", "en": "Result", "uk": "Результат"},
            type=FieldType.text,
            max_length=4096,
        )
    ]
)


@dataclass(frozen=True)
class ExecutorOrderView:
    order: Order
    card: OrderCard


def pack_result(form: FormSchema, values: dict[str, str]) -> dict[str, object]:
    """`text` is what the buyer reads, `files` are Telegram file ids, `fields` the answers."""
    lines: list[str] = []
    files: list[str] = []
    for f in form.fields:
        value = values.get(f.key, "")
        if not value:
            continue
        if f.type is FieldType.file:
            files.append(value)
        elif len(form.fields) == 1:
            lines.append(value)
        else:
            lines.append(f"{pick_i18n(f.label, 'ru')}: {value}")
    return {"text": "\n".join(lines), "files": files, "fields": values}


@dataclass(frozen=True)
class FulfillmentWorkInteractor(BaseInteractor):
    uow: UnitOfWork
    orders: OrdersGateway
    catalog: CatalogGateway
    cards: CardBuilder

    async def my_orders(self, executor_id: int, page: int) -> tuple[list[Order], int, int]:
        """Returns (orders on the page, total orders, corrected page)."""
        total = await self.orders.count_for_executor(executor_id)
        pages = max(1, -(-total // PAGE_SIZE))
        page = min(max(page, 0), pages - 1)
        items = await self.orders.list_for_executor(executor_id, page * PAGE_SIZE, PAGE_SIZE)
        return items, total, page

    async def get(self, executor_id: int, order_id: int) -> ExecutorOrderView | None:
        order = await self.orders.get(order_id)
        if order is None or order.executor_id != executor_id:
            return None
        return ExecutorOrderView(order, await self.cards.build(order, executor_id))

    async def result_form(self, executor_id: int, order_id: int) -> FormSchema:
        order = await self.orders.get(order_id)
        if (
            order is None
            or order.executor_id != executor_id
            or order.status is not OrderStatus.assigned
        ):
            raise OrderUnavailable(order_id)
        return await self._form(order)

    async def _form(self, order: Order) -> FormSchema:
        ctx = await load_context(self.catalog, order)
        schema = ctx.product.result_schema if ctx else None
        form = FormSchema.model_validate(schema or {"fields": []})
        return form if form.fields else DEFAULT_RESULT_FORM

    async def submit(self, executor_id: int, order_id: int, result: dict[str, str]) -> Order:
        try:
            order = await self.orders.get_for_update(order_id)
            if (
                order is None
                or order.executor_id != executor_id
                or order.status is not OrderStatus.assigned
            ):
                raise OrderUnavailable(order_id)
            now = datetime_now()
            # same predicate as the overdue job, evaluated under the same order lock
            if order.deadline_at is not None and order.deadline_at < now:
                raise DeadlineExpired(order_id)
            form = await self._form(order)
            values: dict[str, str] = {}
            for f in form.fields:
                try:
                    values[f.key] = f.validate_value(result.get(f.key, ""))
                except ValueError as e:
                    raise InvalidInput(f"{f.key}: {e}") from e
            order.result = pack_result(form, values)
            order.ready_at = now
            await move(self.orders, order, OrderStatus.ready, executor_id)
            await self.orders.add_event(
                OrderEvent(order_id=order.id, actor_id=executor_id, type="submitted")
            )
            await self.uow.commit()
            return order
        except BaseException:
            await self.uow.rollback()
            raise
