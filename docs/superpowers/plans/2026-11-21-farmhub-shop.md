# FarmHub Shop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Telegram-магазин цифровых товаров с исполнителями, поддержкой, балансом в USDT и Mini App.

**Architecture:** Строим поверх текущего шаблона: `Handler → Flow → Interactor → Presenter → View → Renderer`,
dishka DI, домен = SQLAlchemy-сущности, порты в `app/application/ports`, реализации в `app/infrastructure`.
Деньги — журнал `LedgerEntry`, баланс никогда не хранится отдельным изменяемым полем.

**Tech Stack:** Python 3.12, aiogram 3.33, aiogram-i18n, dishka, FastAPI, SQLAlchemy 2 (asyncpg), Alembic,
Redis, APScheduler, pytest + pytest-asyncio. Mini App: React + Vite + TypeScript (фаза 8).

**Spec:** `docs/superpowers/specs/2026-11-21-farmhub-shop-design.md` — читать целиком перед любой задачей.

**Workflow:** каждая фаза — отдельный исполнитель (Sonnet) и отдельные коммиты по задачам. После фазы Opus
проверяет `git diff` фазы. Подробные задачи фаз 3–9 пишутся перед стартом фазы (`...-phaseN.md`), потому что
опираются на реальный код предыдущих фаз.

## Global Constraints

- Python `>=3.12,<3.13`. aiogram `~=3.33` (НЕ 3.29.0/3.29.1). pydantic `>=2.8`.
- Валюта только USDT, отображение `$`. Деньги — `Decimal`, колонка `Numeric(18, 2)`. float для денег запрещён.
- Время — UTC, `DateTime(timezone=True)`.
- Локали: `ru`, `en`, `uk`. По умолчанию `ru`. Все тексты и эмодзи только в `assets/messages/<locale>/*.ftl`.
- Эмодзи сдержанно, не в каждой строке. Никаких шаблонных «🔥✨» текстов.
- Секреты (токены шлюзов, бота) только в `.env`. Никогда не в коде.
- Слои: `app/application` не импортирует aiogram/FastAPI/SQLAlchemy-сессию напрямую (только порты).
- Каждая задача: `uv run ruff check app tests`, `uv run mypy app` и `uv run pytest` зелёные перед коммитом.
- Коммиты — Conventional Commits, в конце `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.

## Review Focus

1. Два одновременных списания с баланса, которого хватает на одно → проходит ровно одно (T2.3, db-тест).
2. Сумма с 3+ знаками после точки или отрицательная цена → отклоняется, а не округляется молча (T2.1).
3. Недопустимый переход статуса заказа (`completed → in_queue`, `refunded → completed`) → ошибка (T2.1).
4. Ключ есть в одной локали и отсутствует в другой → тест падает (T1.2).
5. Анкета товара с дублирующимся `key`, битым `regex` или `choice` без `options` → ошибка валидации (T2.2).

---

## Дорожная карта

| Фаза | Содержание | План |
|---|---|---|
| 1 | Основа: зависимости, локали, тестовая инфраструктура | этот файл |
| 2 | Модель данных, журнал денег, миграция | этот файл |
| 3 | Бот покупателя: каталог, inline-поиск, карточка, анкета, покупка, выдача `stock`/`fixed`, заказы, баланс, промокоды, тестовый шлюз, ручное пополнение | phase3 |
| 4 | Платежи: порт `PaymentGateway`, CryptoBot / Binance Pay / NOWPayments из `bybit_software_bot`, APScheduler-опрос | phase4 |
| 5 | Исполнители: допуски, очередь/авто, сроки, переписка, «Готово», подтверждение, холд, выплаты через Crypto Pay `transfer`, оценки, чаевые, рейтинг | phase5 |
| 6 | Поддержка: тикеты, закрепление, маршрутизация сообщений (§15) | phase6 |
| 7 | API Mini App: initData-авторизация, REST, WebSocket | phase7 |
| 8 | Mini App (React): покупатель, исполнитель, менеджер | phase8 |
| 9 | Админка в Mini App в полном объёме, рассылки, статистика, журнал | phase9 |

---

## Фаза 1. Основа

### Task 1.1: Обновление зависимостей и переименование

**Files:**
- Modify: `pyproject.toml`, `uv.lock`, `README.md` (заголовок, автор)
- Modify: всё, что сломает aiogram 3.33 (фильтры, возвращающие awaitable; `dp.update.filter`)

**Interfaces:**
- Produces: окружение `uv sync` с aiogram 3.33, pytest, pytest-asyncio.

- [ ] **Step 1:** `pyproject.toml`: `name = "farmhub_shop"`, `description` по-новому, убрать `authors`/`urls` шаблона.
  Зависимости: `aiogram~=3.33.0`, `aiogram-i18n` последняя, `pydantic>=2.8`, `pydantic-settings[yaml]` последняя
  совместимая, остальные — до последних совместимых версий. В dev: `pytest>=8`, `pytest-asyncio>=0.24`.
  `[tool.ruff] target-version = "py312"`. Добавить
  `[tool.pytest.ini_options] asyncio_mode = "auto"`, `testpaths = ["tests"]`, `markers = ["db: needs TEST_POSTGRES_DSN"]`.
- [ ] **Step 2:** `uv lock && uv sync`. Expected: без ошибок, `uv run python -c "import aiogram; print(aiogram.__version__)"` → `3.33.x`.
- [ ] **Step 3:** `uv run python -c "import app.__main__"` и `uv run mypy app`. Исправить всё, что сломалось
  от апгрейда (см. changelog 3.21–3.33). Expected: импорт без ошибок, mypy без новых ошибок.
- [ ] **Step 4:** Commit `chore: upgrade aiogram to 3.33 and rename project`.

### Task 1.2: Локали ru/en/uk и чистка шаблона

**Files:**
- Delete: `assets/messages/*/deposit.ftl`, `CDDeposit`, `deposit_keyboard`, `answer_deposit` (flow, handler, presenter)
- Create: `assets/messages/ru/{menu,errors}.ftl`
- Modify: `assets/messages/{en,uk}/{menu,errors}.ftl`, `app/const.py` (`DEFAULT_LOCALE = Locale.RU`),
  `.env.dist` (`TELEGRAM_LOCALES=ru,en,uk`), `app/presentation/telegram/presenters/common/menu.py`
- Test: `tests/test_locales.py`

- [ ] **Step 1: Write the failing test** `tests/test_locales.py`:

```python
from app.const import MESSAGES_SOURCE_DIR

LOCALES = ("ru", "en", "uk")

def _keys(locale: str) -> set[str]:
    keys = set()
    for f in (MESSAGES_SOURCE_DIR / locale).glob("*.ftl"):
        for line in f.read_text(encoding="utf-8").splitlines():
            if line and not line[0].isspace() and "=" in line and not line.startswith("#"):
                keys.add(line.split("=", 1)[0].strip())
    return keys

def test_all_locales_have_same_keys():
    base = _keys("ru")
    assert base, "ru locale is empty"
    for loc in LOCALES[1:]:
        assert _keys(loc) == base, f"{loc} differs: {_keys(loc) ^ base}"
```

- [ ] **Step 2:** `uv run pytest tests/test_locales.py -v` → FAIL (нет `ru`).
- [ ] **Step 3:** Создать `ru`, убрать deposit-тексты везде. Приветствие: нейтральное, без «депай» и без эмодзи-шума,
  например `messages-greeting = Здравствуйте, { $name }.` + строка о магазине. Кнопку deposit из меню убрать
  (меню будет в фазе 3).
- [ ] **Step 4:** `uv run pytest tests/test_locales.py -v` → PASS. `uv run mypy app` чисто.
- [ ] **Step 5:** Commit `feat: add ru locale, drop template deposit texts`.

### Task 1.3: Тестовая инфраструктура БД и UoW с одной транзакцией

**Files:**
- Create: `tests/__init__.py`, `tests/conftest.py`
- Modify: `app/infrastructure/postgres/uow.py`
- Modify: `migrations/versions/001_initial.py` (в `downgrade` удалить строку `op.drop_table("products_data")`)
- Test: `tests/infrastructure/test_uow.py`

**Interfaces:**
- Produces: фикстура `session: AsyncSession` (db-тесты, схема из `Base.metadata.create_all`, откат после теста);
  маркер `db` — тест пропускается, если нет env `TEST_POSTGRES_DSN` (`postgresql+asyncpg://...`).
- Produces: `UoW.flush() -> None` (добавить без коммита), `UoW.commit(*instances)` — как сейчас.

- [ ] **Step 1:** `tests/conftest.py`: если `TEST_POSTGRES_DSN` не задан — `pytest.skip` для тестов с маркером `db`
  (через `pytest_collection_modifyitems`). Фикстура `engine` (session-scope): `create_async_engine`, `drop_all` + `create_all`.
  Фикстура `session`: соединение → `begin()` → `AsyncSession(bind=conn, join_transaction_mode="create_savepoint")` →
  после теста `rollback()`.
- [ ] **Step 2: failing test** `tests/infrastructure/test_uow.py`:

```python
import pytest
from app.domain.user import User
from app.infrastructure.postgres.uow import UoW

@pytest.mark.db
async def test_flush_makes_row_visible_in_same_session(session):
    uow = UoW(session)
    session.add(User(id=1, name="a", language="ru", language_code=None))
    await uow.flush()
    assert await session.get(User, 1) is not None
```

- [ ] **Step 3:** Добавить `async def flush(self, *instances: Base) -> None` (add_all + flush). Run с поднятым Postgres:
  `TEST_POSTGRES_DSN=... uv run pytest -m db -v` → PASS. Без DSN: `uv run pytest` → тест SKIPPED, не FAIL.
- [ ] **Step 4:** Commit `test: add pytest infrastructure and UoW.flush`.

---

## Фаза 2. Модель данных

Все сущности — в `app/domain/`, по файлу на агрегат. Регистрировать в `app/domain/__init__.py`, чтобы Alembic их видел.

### Task 2.1: Деньги, перечисления, статусы заказа

**Files:**
- Modify: `app/utils/custom_types.py` (`Money: TypeAlias = Annotated[Decimal, "money"]`)
- Modify: `app/domain/base.py` (registry: `Money: Numeric(18, 2)`, `DictStrAny: JSONB()` вместо `JSON()`)
- Create: `app/domain/money.py`, `app/domain/enums/{order,ledger,roles,catalog,support}.py`, `app/domain/order_status.py`
- Test: `tests/domain/test_money.py`, `tests/domain/test_order_status.py`

**Interfaces:**
- Produces:
  - `money(value: str | int | Decimal) -> Decimal` в `app/domain/money.py`: `ValueError`, если больше 2 знаков после точки
    или не конечное число. Float на вход — `TypeError`.
  - `percent_of(amount: Decimal, percent: Decimal) -> Decimal` — `ROUND_HALF_UP` до 0.01.
  - `OrderStatus(StrEnum)`: `awaiting_input, paid, in_queue, assigned, ready, completed, failed, refunded, cancelled`.
  - `LedgerAccount(StrEnum)`: `main, executor_hold, executor_available`.
  - `LedgerKind(StrEnum)`: `topup, purchase, refund, executor_earning, earning_reversal, hold_release, tip,
    withdrawal, promo_bonus, admin_adjust`.
  - `Role(IntFlag)`: `OWNER=1, ADMIN=2, MANAGER=4, EXECUTOR=8, CAN_CATALOG=16, CAN_FINANCE=32, CAN_USERS=64,
    CAN_BROADCAST=128`.
  - `AssignMode(StrEnum)`: `queue, auto`. `TicketStatus(StrEnum)`: `open, taken, closed`.
    `ConversationKind(StrEnum)`: `ticket, order`. `WithdrawalStatus(StrEnum)`: `pending, approved, paid, rejected`.
    `PaymentStatus(StrEnum)`: `created, pending, partially_paid, canceled, success`.
  - `ensure_transition(current: OrderStatus, new: OrderStatus) -> None` в `app/domain/order_status.py`,
    `InvalidTransition(Exception)`. Разрешённые переходы (ровно эти):

```python
ALLOWED = {
    OrderStatus.awaiting_input: {OrderStatus.paid, OrderStatus.cancelled},
    OrderStatus.paid: {OrderStatus.in_queue, OrderStatus.completed, OrderStatus.failed},
    OrderStatus.in_queue: {OrderStatus.assigned, OrderStatus.cancelled, OrderStatus.failed},
    OrderStatus.assigned: {OrderStatus.in_queue, OrderStatus.ready, OrderStatus.failed},
    OrderStatus.ready: {OrderStatus.completed, OrderStatus.assigned, OrderStatus.failed},
    OrderStatus.completed: {OrderStatus.refunded},
    OrderStatus.failed: {OrderStatus.refunded},
    OrderStatus.refunded: set(), OrderStatus.cancelled: set(),
}
```

- [ ] **Step 1: failing tests:**

```python
# tests/domain/test_money.py
from decimal import Decimal
import pytest
from app.domain.money import money, percent_of

def test_money_parses_two_decimals():
    assert money("10.50") == Decimal("10.50")

@pytest.mark.parametrize("bad", ["10.555", "NaN", "Infinity", "abc"])
def test_money_rejects(bad):
    with pytest.raises(ValueError):
        money(bad)

def test_money_rejects_float():
    with pytest.raises(TypeError):
        money(0.1)  # type: ignore[arg-type]

def test_percent_rounds_half_up():
    assert percent_of(Decimal("10.05"), Decimal("15")) == Decimal("1.51")
```

```python
# tests/domain/test_order_status.py
import pytest
from app.domain.enums.order import OrderStatus as S
from app.domain.order_status import InvalidTransition, ensure_transition

def test_allowed():
    ensure_transition(S.assigned, S.ready)

@pytest.mark.parametrize("a,b", [(S.completed, S.in_queue), (S.refunded, S.completed), (S.cancelled, S.paid)])
def test_forbidden(a, b):
    with pytest.raises(InvalidTransition):
        ensure_transition(a, b)
```

- [ ] **Step 2:** `uv run pytest tests/domain -v` → FAIL (нет модулей).
- [ ] **Step 3:** Реализовать. Отрицательные суммы `money()` разрешает (журнал хранит знак); запрет отрицательной цены — в T2.2.
- [ ] **Step 4:** `uv run pytest tests/domain -v` → PASS. Commit `feat(domain): money type, enums, order state machine`.

### Task 2.2: Каталог, заказы, схема анкеты

**Files:**
- Create: `app/domain/catalog.py` (`Category, Service, Country, Product, ProductVariant, StockUnit`),
  `app/domain/order.py` (`Order, OrderEvent`), `app/application/models/form_schema.py`
- Modify: `app/domain/user.py` (`roles: Mapped[int] = mapped_column(default=0, server_default="0")`)
- Test: `tests/application/test_form_schema.py`, `tests/domain/test_catalog_db.py` (db)

**Interfaces:**
- Produces: поля сущностей — ровно как в spec §6 (имена колонок оттуда). Дополнительно:
  - `Category.parent_id` FK на `categories.id` `ondelete="RESTRICT"`.
  - `ProductVariant.price: Money` + `CheckConstraint("price >= 0")`.
  - `StockUnit.sold_order_id` FK на `orders.id`, nullable; индекс `(variant_id, sold_order_id)`.
  - `Order.price: Money`, `Order.discount: Money` (default 0), `Order.promo_code_id` nullable,
    `Order.hold_until`, `Order.review_due_at` nullable datetimes (нужны планировщику).
  - Индексы `Order(status)`, `Order(executor_id, status)`, `Order(user_id)`.
- Produces (`app/application/models/form_schema.py`, pydantic):
  - `FieldType(StrEnum)`: `text, email, number, choice, login, file`.
  - `FormField(key: str, label: dict[str, str], type: FieldType, required: bool = True, regex: str | None = None,
    options: list[str] | None = None, hidden_from_executor: bool = False)`.
  - `FormSchema(fields: list[FormField])`. Валидация: уникальные `key` (`^[a-z][a-z0-9_]{0,31}$`), `regex`
    компилируется, `choice` требует непустые `options`, `label` содержит `ru`.
  - `FormSchema.validate_answer(key: str, raw: str) -> str` — проверка одного ответа (email, number, choice, regex),
    `ValueError` при ошибке. Используется для `input_schema` и `result_schema`.

- [ ] **Step 1: failing tests** `tests/application/test_form_schema.py`:
  - `test_duplicate_keys_rejected`, `test_bad_regex_rejected`, `test_choice_without_options_rejected`,
    `test_label_requires_ru` — все `pytest.raises(ValidationError)`.
  - `test_validate_answer_email`: `"a@b.co"` ок, `"nope"` → `ValueError`.
  - `test_validate_answer_choice`: значение вне `options` → `ValueError`.
- [ ] **Step 2:** db-тест `tests/domain/test_catalog_db.py`: создать дерево категория→подкатегория, товар с двумя вариантами
  (`TR` 5.00, `KZ` 7.00); вариант с `price=-1` → `IntegrityError` при flush.
- [ ] **Step 3:** Реализовать. Run `uv run pytest -v` → PASS (db-тесты PASS при наличии DSN).
- [ ] **Step 4:** Commit `feat(domain): catalog, orders, form schema`.

### Task 2.3: Журнал денег и сервис проводок

**Files:**
- Create: `app/domain/ledger.py` (`LedgerEntry, Payment, Withdrawal`)
- Create: `app/application/ports/repositories/ledger.py` (`LedgerGateway` Protocol)
- Create: `app/infrastructure/postgres/repositories/ledger.py` (`LedgerRepository`)
- Create: `app/application/interactors/ledger.py` (`LedgerService`)
- Modify: `app/providers/infrastructure/repositories.py`, `app/providers/handling/interactors.py`
- Test: `tests/application/test_ledger_db.py` (db)

**Interfaces:**
- Produces:
  - `LedgerEntry` — поля из spec §6; `amount != 0` CheckConstraint; индекс `(user_id, account, id)`.
  - `Payment` — `unique(provider, external_id)`. `Withdrawal` — поля §6.
  - `LedgerGateway.lock_user(user_id: int) -> None` (`SELECT ... FROM users WHERE id=:id FOR UPDATE`),
    `balance(user_id: int, account: LedgerAccount) -> Decimal` (сумма, 0 если пусто), `add(entry: LedgerEntry) -> None`.
  - `LedgerService.post(user_id: int, account: LedgerAccount, amount: Decimal, kind: LedgerKind, *,
    order_id: int | None = None, ref: str | None = None) -> LedgerEntry` — блокирует пользователя, считает баланс,
    пишет запись с `balance_after`. Для `main` и `executor_available` итог `< 0` → `InsufficientFunds`.
    **Не коммитит** — коммит делает вызывающий интерактор (одна транзакция на операцию).
  - `InsufficientFunds(Exception)` в `app/application/errors/base.py`.

- [ ] **Step 1: failing db-tests:**
  - `test_post_updates_balance_after`: `+10.00` topup, `-3.50` purchase → `balance == 6.50`, последний `balance_after == 6.50`.
  - `test_overdraft_rejected`: баланс 5, списание 6 → `InsufficientFunds`, записей не добавилось.
  - `test_hold_account_may_not_go_below_zero_either_way`: `executor_hold` +5 → `earning_reversal` −5 → 0.
  - `test_concurrent_spend_only_one_wins`: баланс 10; две **отдельные** сессии/соединения одновременно
    (`asyncio.gather`) списывают по 7 и коммитят → ровно одна успешна, другая `InsufficientFunds`, итог 3.00.
- [ ] **Step 2:** Run → FAIL. **Step 3:** Реализовать. **Step 4:** Run → PASS.
- [ ] **Step 5:** Commit `feat: ledger with row-locked postings`.

### Task 2.4: Люди, поддержка, промокоды, настройки

**Files:**
- Create: `app/domain/executor.py` (`ExecutorProfile, ExecutorPermission`), `app/domain/support.py`
  (`Ticket, Conversation, Message`), `app/domain/review.py` (`OrderReview`), `app/domain/promo.py`
  (`PromoCode, PromoCodeUsage`), `app/domain/settings.py` (`Setting`), `app/domain/audit.py` (`AuditLog`),
  `app/domain/broadcast.py` (`Broadcast`)
- Test: `tests/domain/test_people_db.py` (db)

**Interfaces:**
- Produces: поля по spec §6 и §15a. Уточнения:
  - `ExecutorPermission` — PK `(executor_id, service_id, country_code)`.
  - `ExecutorProfile.alias` unique.
  - `Conversation.thread_id` nullable; `Message.tg_message_id` + `Message.tg_chat_id`, индекс по паре
    (для маршрутизации ответа по reply).
  - `PromoCode`: `code` unique (хранить UPPER), `discount_percent`, `discount_amount`, `bonus_amount` (бонус на баланс),
    `usage_limit`, `times_used`, `expires_at`, `product_id`, `min_amount`, `new_users_only`, `allowed_user_ids: list[int]`,
    `reusable`, `active`. CheckConstraint: задано ровно одно из `discount_percent`, `discount_amount`, `bonus_amount`.
  - `OrderReview.order_id` unique, `score` CheckConstraint `1..5`.
- [ ] **Step 1: failing db-tests:** промокод с двумя видами сразу → `IntegrityError`; повторный отзыв на заказ →
  `IntegrityError`; `score=6` → `IntegrityError`.
- [ ] **Step 2–4:** Run FAIL → реализовать → PASS.
- [ ] **Step 5:** Commit `feat(domain): executors, support, promo codes, settings, audit`.

### Task 2.5: Миграция 002

**Files:**
- Create: `migrations/versions/002_shop_schema.py`

- [ ] **Step 1:** Поднять Postgres (`make app-run-db` или свой), `make migrate` (001), затем
  `make migration message=shop_schema`. Проверить, что миграция содержит все таблицы, CheckConstraint и индексы,
  а `downgrade` удаляет их в обратном порядке.
- [ ] **Step 2:** `uv run alembic downgrade base && uv run alembic upgrade head` → без ошибок.
- [ ] **Step 3:** Commit `feat(db): migration 002 shop schema`.
