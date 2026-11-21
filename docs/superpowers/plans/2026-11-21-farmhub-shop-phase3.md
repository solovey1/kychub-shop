# FarmHub Shop — Фаза 3: бот покупателя

> Executor: Sonnet. Читать вместе с `2026-11-21-farmhub-shop.md` (Global Constraints) и spec
> `docs/superpowers/specs/2026-11-21-farmhub-shop-design.md` (§6, §7, §10, §15, §15a).

**Goal:** покупатель в боте видит каталог, ищет товар через поле ввода, заполняет анкету, платит с баланса,
получает товар (`stock`/`fixed`) или заказ уходит в работу (`manual`/`executor`), видит заказы и баланс,
пополняет баланс тестовым шлюзом, активирует промокоды. Админ пополняет баланс вручную.

**Тесты не пишем** (решение заказчика). Проверка каждой задачи: `uv run ruff check app`, `uv run mypy app`
(только 2 известные ошибки rowcount), `uv run python -c "import app.__main__"`. Ручная проверка — заказчик.

## Общие решения фазы

- Слои как в README: handler → flow → interactor → presenter → renderer. Interactor не знает aiogram.
  Каждое денежное действие — один interactor-метод, одна транзакция, один `commit()` в конце.
- Новые порты в `app/application/ports/repositories/`, реализации в `app/infrastructure/postgres/repositories/`,
  регистрация в `RepositoriesProvider`, interactors — в `InteractorsProvider`, flows/presenters — в своих провайдерах.
- Локализованные поля (`title_i18n` и т.п.): `pick_i18n(d: dict[str, str] | None, locale: str) -> str` в
  `app/application/i18n_text.py`: locale → `ru` → первое значение → `""`.
- Деньги на экране: `fmt_usd(amount: Decimal) -> str` → `"$12.50"` (там же или `app/domain/money.py`).
- Кнопки: `style="success"` для оплаты/подтверждения, `"danger"` для отмены, `"primary"` для главного действия
  экрана. Эмодзи только в `.ftl`, сдержанно.
- Флаг страны вычислять из ISO-кода (regional indicator), не хранить.
- Пагинация списков — 8 элементов на страницу.
- Все тексты — ключи в `assets/messages/{ru,en,uk}/*.ftl`, ключи одинаковые во всех трёх (есть `tests/test_locales.py`).

## Review Focus (проверить руками в ревью)

1. Двойное нажатие «Оплатить» → одно списание и один заказ (идемпотентность по `purchase_token`).
2. Последняя единица склада, два покупателя одновременно → один получает товар, второму «нет в наличии»,
   деньги второго не списаны (`FOR UPDATE SKIP LOCKED` внутри той же транзакции).
3. Промокод с `usage_limit=1`, двое одновременно → применяется один раз (строка промокода `FOR UPDATE`).
4. Ответ в анкете не проходит проверку → бот повторяет вопрос с причиной, состояние не теряется.
5. Результат длиннее 256 символов → без `copy_text`; длиннее 3500 → отправляется `.txt` файлом.

---

### Task 3.1: Владельцы, роли, админ-фильтр, демо-данные

**Files:**
- Modify: `app/application/models/config/env/common.py` (+ `owner_ids: StringList`), `.env.dist`
  (`COMMON_OWNER_IDS=123,456`)
- Modify: `app/providers/infrastructure/request.py` (`provide_user`): если `user.id in owner_ids` и у него нет
  `Role.OWNER` → выставить `OWNER | ADMIN | CAN_CATALOG | CAN_FINANCE | CAN_USERS | CAN_BROADCAST` и сохранить.
- Modify: `app/presentation/telegram/filters/__init__.py`: `ADMIN_FILTER` → фильтр по роли:
  `HasRole(Role.ADMIN)` (класс в `filters/roles.py`, проверяет `user.roles & role` у `User` из dishka/middleware).
  Админ-хендлеры работают в личке админа, не в `admin_chat_id`. `admin_chat_id` остаётся для уведомлений.
- Create: `scripts/seed_demo.py` — создаёт через `AppConfig` + сессию: страны TR, KZ, US; сервис `steam`
  (deadline 120, percent 70, queue); дерево «Аккаунты → Steam», «Ключи»; товары:
  1. «Регистрация Steam» (`executor`, service steam, варианты TR $5.00 и KZ $7.00, анкета: поле `email` типа email);
  2. «Ключ Windows» (`stock`, один вариант $10.00, 3 единицы склада);
  3. «Гайд PDF» (`fixed`, $2.00, config `{"text": "https://example.com/guide"}`);
  4. «Индивидуальный заказ» (`manual`, $15.00, анкета: поле `details` типа text).
  Скрипт идемпотентен (повторный запуск не дублирует — проверка по `services.code` / названию).
- Create: `app/application/i18n_text.py` (`pick_i18n`, `fmt_usd`).

Commit: `feat: owner roles, role-based admin filter, demo seed`.

### Task 3.2: Каталог и inline-поиск

**Files:**
- Create: `app/application/ports/repositories/catalog.py` (`CatalogGateway`),
  `app/infrastructure/postgres/repositories/catalog.py`
- Create: `app/application/interactors/catalog.py` (`CatalogInteractor`)
- Create: `app/presentation/telegram/{callbacks,keyboards,presenters/common,flows/common,handlers/main}/catalog.py`,
  `handlers/main/inline.py`
- Modify: `assets/messages/*/catalog.ftl` (новый файл в каждой локали)

**Interfaces:**
- `CatalogGateway`:
  - `children(parent_id: int | None) -> list[Category]` (только `is_active`, по `position, id`)
  - `products(category_id: int, offset: int, limit: int) -> list[Product]` и `count_products(category_id) -> int`
  - `product(product_id: int) -> Product | None`, `variants(product_id: int) -> list[ProductVariant]` (активные, по цене)
  - `variant(variant_id: int) -> ProductVariant | None`
  - `available_stock(variant_ids: list[int]) -> dict[int, int]` — непроданные единицы; бессрочные считать как 1+
  - `search(text: str, locale: str, offset: int, limit: int) -> list[tuple[Product, Decimal]]` — `ILIKE` по
    `title_i18n ->> locale` и `title_i18n ->> 'ru'`, только активные, с минимальной ценой варианта.
- Callback data: `CDCategory(id: int = 0, page: int = 0)` (0 = корень), `CDProduct(id: int)`, `CDVariant(id: int)`.
- Экран категории: подкатегории кнопками, затем товары страницы, внизу пагинация и «Назад» (к родителю / в меню).
- Карточка товара: название, описание, кнопка на каждый вариант `🇹🇷 Турция — $5.00` (без страны — просто цена).
  Для `stock` вариант без наличия → кнопка `disabled` («нет в наличии»).
- Inline: хендлер `inline_query`, ответ `answer_inline_query(results, cache_time=5, is_personal=True,
  next_offset=...)`, до 20 результатов на страницу. Результат — `InlineQueryResultArticle` (title, description
  «от $X»), `input_message_content` — короткий текст с названием, `reply_markup` — кнопка «Открыть» → `CDProduct`.
  Пустой запрос → первые активные товары.
- Inline-режим должен быть включён в @BotFather — указать в README (раздел запуска).

Commit: `feat: catalog browsing and inline search`.

### Task 3.3: Покупка: анкета, промокод-скидка, оплата, выдача

**Files:**
- Create: `app/application/ports/repositories/{orders,stock,promo}.py` + реализации
- Create: `app/application/fulfillment/{__init__,base,stock,fixed,manual,executor}.py`
- Create: `app/application/interactors/purchase.py` (`PurchaseInteractor`)
- Create: `app/presentation/telegram/{states/purchase.py, callbacks/purchase.py, keyboards/purchase.py,
  presenters/common/purchase.py, flows/common/purchase.py, handlers/main/purchase.py}`
- Create: `assets/messages/*/purchase.ftl`
- Create: `app/providers/handling/fulfillment.py` (реестр)

**Interfaces:**
- Fulfillment (application, без aiogram):

```python
class FulfillmentHandler(Protocol):
    code: ClassVar[str]
    def validate_config(self, config: dict[str, Any]) -> None: ...
    async def on_paid(self, order: Order, product: Product) -> None:
        """Внутри транзакции покупки. Может поднять OutOfStock. Меняет order.status/result."""

FulfillmentRegistry = NewType("FulfillmentRegistry", dict[str, FulfillmentHandler])
```

  - `stock`: `StockGateway.take(variant_id: int, order_id: int) -> StockUnit | None` — сначала непроданная
    единица `FOR UPDATE SKIP LOCKED` (ставит `sold_order_id`), иначе бессрочная (`is_unlimited`, не помечается).
    Нет → `OutOfStock(AppError)`. `order.result = {"text": unit.payload}`, `paid → completed`, `completed_at`.
  - `fixed`: `order.result = {"text": config["text"]}`, `paid → completed`. `validate_config` требует `text`.
  - `manual`: статус остаётся `paid` (ждёт админа, фаза 9).
  - `executor`: `paid → in_queue` (очередь и назначение — фаза 5).
  - Каждая смена статуса — через `ensure_transition` + `OrderEvent`.
- `PurchaseInteractor`:
  - `quote(user_id: int, variant_id: int, promo_code: str | None) -> Quote` — `Quote(price, discount, total,
    promo_code_id | None, promo_error: str | None)`; без записи в БД.
  - `purchase(user_id: int, variant_id: int, input_data: dict[str, str], promo_code: str | None,
    purchase_token: str) -> Order` — одна транзакция:
    1. `LedgerGateway.get_by_ref(purchase, f"purchase:{purchase_token}")` есть → вернуть его заказ (повтор).
    2. Вариант и товар активны, иначе `ProductUnavailable(AppError)`.
    3. Промокод (если указан): `SELECT ... FOR UPDATE` строки, проверки: `active`, не истёк, `times_used < usage_limit`,
       `product_id` совпадает/пусто, `min_amount`, `new_users_only` (нет ни одной записи `purchase` в журнале),
       `allowed_user_ids` пусто или содержит пользователя, `reusable` или нет записи в `promo_code_usages`,
       только скидочный вид (`bonus_amount` → ошибка «это бонусный код»). `times_used += 1`, запись usage.
       Скидка: процент через `percent_of`, сумма — `min(discount_amount, price)`.
    4. `Order(status=paid, price, discount, snapshot={"product": title_i18n, "variant": title/country, "price": str},
       input_data, promo_code_id)`, `flush()`.
    5. `LedgerService.post(user_id, main, -(price - discount), purchase, order_id=order.id,
       ref=f"purchase:{purchase_token}")` — при нуле к оплате проводку не делать.
    6. `registry[product.fulfillment_type].on_paid(order, product)`.
    7. `commit()`. Любое исключение → `rollback()` и проброс.
- FSM `PurchaseForm.answer`: данные `variant_id, idx, answers, purchase_token, promo_code`. Поля анкеты —
  `FormSchema.model_validate(product.input_schema or {"fields": []})`. Вопрос — `label` по локали, `force_reply`;
  `choice` — кнопки; `file` — принимать document/photo, хранить `file_id`. Ошибка `validate_value` →
  повторить вопрос с причиной. Кнопка «Отмена» (`danger`) на каждом шаге.
- Экран подтверждения: товар, вариант, ответы (кроме `file`), цена, скидка, итог, баланс. Кнопки:
  «Оплатить $X» (`success`), «Промокод», «Отмена» (`danger`). `purchase_token = uuid4().hex` создаётся при показе
  экрана и хранится в FSM.
- Не хватает денег → текст с недостающей суммой и кнопка «Пополнить» (→ экран пополнения из 3.4).
- После оплаты: `completed` → сообщение с результатом: текст в `<code>`, кнопка `copy_text` если ≤256 символов;
  если >3500 — `BufferedInputFile` `.txt`. `in_queue`/`paid` → «Заказ №N принят в работу». `manual` →
  уведомление в `config.common.admin_chat_id` с номером заказа и анкетой.

Commit: `feat: purchase flow with questionnaire, promo discount and fulfillment registry`.

### Task 3.4: Заказы, баланс, пополнение, бонус-промокод, ручное пополнение

**Files:**
- Create: interactors `app/application/interactors/{orders,balance}.py`, соответствующие presenters/flows/handlers/
  keyboards/callbacks, `assets/messages/*/{orders,balance}.ftl`
- Create: `app/domain/enums/order.py` локализация статусов — ключи `order-status-<status>` в ftl.

**Interfaces:**
- `OrdersInteractor.list(user_id, page) -> (list[Order], total)`, `get(user_id, order_id) -> Order | None`
  (только свой заказ — чужой → None).
- Экран заказа: №, товар/вариант из `snapshot`, статус, дата, сумма; `completed` → результат как в 3.3.
- `BalanceInteractor`:
  - `summary(user_id) -> (Decimal, list[LedgerEntry])` — баланс `main` и последние 10 записей.
  - `test_topup(user_id, amount: Decimal) -> Payment` — только если `config.common.test_payments` (новое поле
    `COMMON_TEST_PAYMENTS=false` по умолчанию): `Payment(provider="test", external_id=uuid, status=success)`,
    проводка `topup` с `ref=f"payment:{payment.id}"`, commit.
  - `redeem_bonus(user_id, code: str) -> Decimal` — промокод с `bonus_amount`, те же проверки и блокировка, что в 3.3,
    проводка `promo_bonus` с `ref=f"promo:{promo.id}:{user_id}"` для не-`reusable` (для `reusable` —
    `ref=f"promo:{promo.id}:{user_id}:{times_used}"`).
  - `admin_topup(admin_id, user_id, amount: Decimal, comment: str) -> LedgerEntry` — `admin_adjust`
    (отрицательная сумма = списание), `AuditLog(action="balance.adjust")`, commit.
- Экран баланса: сумма, история (тип, сумма со знаком, дата), кнопки «Пополнить», «Активировать промокод».
  Пополнение: суммы 5 / 10 / 25 / 50 / своя. Если тестовые платежи выключены → «Пополнение скоро будет доступно».
- Админ-команда в личке: `/topup <user_id> <amount> [комментарий]` (фильтр `HasRole(Role.CAN_FINANCE)`),
  пользователю приходит уведомление о зачислении.

Commit: `feat: orders, balance, test top-up, bonus promo codes, admin top-up`.

### Task 3.5: Главное меню, язык, команды

**Files:** `handlers/main/menu.py`, `presenters/common/menu.py`, `keyboards/menu.py`, `assets/commands.yml`,
`assets/messages/*/menu.ftl`

- Меню (одно «живое» сообщение, редактируется): «Каталог» (`primary`), «Поиск» (`switch_inline_query_current_chat=""`),
  «Мои заказы», «Баланс: $X», «Язык». Поддержку добавит фаза 6.
- Язык: экран с тремя кнопками ru/en/uk → `UserManager.set_locale` → меню перерисовывается на новом языке.
- `commands.yml`: `start` (меню), `catalog`, `orders`, `balance` для `ru`, `en`, `uk`; хендлеры команд ведут на экраны.

Commit: `feat: main menu, language switch, bot commands`.
