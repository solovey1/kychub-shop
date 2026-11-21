# FarmHub Shop — Фаза 4: платежи

> Executor: Sonnet. Читать вместе с `2026-11-21-farmhub-shop.md` (Global Constraints) и spec §15b.
> Источник для переноса: `D:\Coding\Crypto\bybit_software_bot\app\services\payment_providers\` (gateways + services),
> `app\scheduler\tasks\payment.py`, `app\services\payment.py`. Переписать под стиль этого проекта (порты, dishka,
> конфиг через pydantic-settings), не копировать `os.getenv`/`load_dotenv` и захардкоженные токены.

**Goal:** пополнение баланса через CryptoBot (Crypto Pay), Binance Pay и NOWPayments с опросом статусов
по расписанию и идемпотентным зачислением.

**Тесты не пишем.** Проверка: ruff, mypy (2 известные ошибки), `import app.__main__`, dishka-граф (одноразовый скрипт).

## Решения

- Порт `app/application/ports/payments.py`:

```python
@dataclass(frozen=True)
class CreatedPayment:
    pay_id: str
    url: str | None          # None — показать инструкцию (Binance Pay)

class PaymentGateway(Protocol):
    code: ClassVar[str]      # "cryptobot" | "binance" | "nowpayments" | "test"
    async def create_payment(self, amount: Decimal, payment_id: str, description: str) -> CreatedPayment: ...
    async def get_status(self, pay_id: str, amount: Decimal) -> PaymentStatus: ...

PaymentGateways = NewType("PaymentGateways", dict[str, PaymentGateway])
```

- Реализации `app/infrastructure/payments/{cryptopay,binance,nowpayments,test}.py`. HTTP — один `aiohttp.ClientSession`
  на приложение (APP-scope провайдер) или клиент библиотеки (`aiocryptopay`) с закрытием на shutdown.
- Конфиг `PaymentsConfig(env_prefix="PAYMENTS_")`: `cryptopay_token: SecretStr | None`, `cryptopay_network`
  (`mainnet`/`testnet`), `binance_api_key`, `binance_api_secret: SecretStr | None`, `binance_pay_id: str | None`
  (показывается покупателю), `nowpayments_api_key`, `nowpayments_login`, `nowpayments_password: SecretStr | None`,
  `min_topup: Decimal = 1`, `max_topup: Decimal = 10000`. Шлюз включён, только если заданы его ключи.
  `test` включён при `COMMON_TEST_PAYMENTS=true` (уже есть из фазы 3 — перевести `test_topup` на этот порт).
  Добавить переменные в `.env.dist` с пустыми значениями.
- Статусы шлюзов маппятся в `PaymentStatus` (`created, pending, partially_paid, canceled, success`).
  Двигаются только вперёд: порядок `created=0, pending=1, partially_paid=1, canceled=2, success=3`.
- Binance Pay: `create_payment` ничего не вызывает, `pay_id = payment_id`; покупатель переводит сумму на
  `binance_pay_id` с примечанием = `payment_id`; `get_status` ищет перевод по примечанию и сумме ≥ ожидаемой.
- `TopupInteractor` (`app/application/interactors/topup.py`):
  - `create(user_id, amount: Decimal, provider: str) -> tuple[Payment, CreatedPayment]` — проверка `min/max`,
    `payment_id = uuid4().hex`, вызов шлюза, затем `Payment(provider, external_id=pay_id, amount, status=created,
    raw={"payment_id": payment_id})`, commit.
  - `check(payment_id: int) -> Payment` — опрос шлюза, движение статуса вперёд; `success` → `credit()`.
  - `credit(payment_id: int) -> bool` — одна транзакция: `SELECT payments ... FOR UPDATE`; ledger `topup` с
    `ref=f"payment:{payment.id}"` (идемпотентно), `status=success`, commit. Возвращает True, если зачислено сейчас.
  - `pending(max_age: timedelta) -> list[Payment]`, `unfulfilled_success() -> list[Payment]` (success без проводки).
- Планировщик: `apscheduler>=3.11` (`AsyncIOScheduler`), модуль `app/infrastructure/scheduler/`:
  `create_scheduler(container) -> AsyncIOScheduler`, старт/стоп в `LifespanService` (и для polling, и для webhook).
  Каждая задача открывает `async with container() as request:` и берёт interactor оттуда. Задачи:
  `poll_payments` раз в 60 с (pending младше 24 ч), `retry_unfulfilled` раз в 180 с. `max_instances=1`.
  Этот же планировщик будут использовать фазы 5–6.
- Уведомление о зачислении: после `credit() == True` бот пишет пользователю на его языке
  («Баланс пополнен на $X»). Отправка — через `Bot` и i18n core, ошибки отправки логировать, не падать.
- UI (дополнить экран пополнения из фазы 3): сумма → выбор способа (кнопки только включённых шлюзов) →
  сообщение со ссылкой-кнопкой «Оплатить» (или инструкцией для Binance Pay с `copy_text` для Pay ID и примечания)
  и кнопкой «Проверить оплату» (`TopupInteractor.check`). Счёт живёт 1 час — сказать об этом в тексте.
- Зависимости: `aiocryptopay`, `apscheduler`. Ничего больше.

## Review Focus

1. Одна оплата опрошена планировщиком и кнопкой «Проверить» одновременно → одно зачисление (FOR UPDATE + ref).
2. Шлюз недоступен/таймаут → задача логирует и идёт дальше, статус не меняется.
3. NOWPayments `partially_paid` → не зачислять.
4. Binance-перевод с меньшей суммой → не зачислять.
5. Сумма пополнения вне `min/max` или с 3 знаками → понятная ошибка в боте.

## Задачи и коммиты

1. `feat(payments): gateway port, config and provider implementations` — порт, конфиг, 4 реализации, провайдер dishka.
2. `feat(payments): top-up interactor and scheduler polling` — interactor, APScheduler, задачи, уведомление.
3. `feat(payments): top-up screens for real gateways` — UI, ftl ru/en/uk.
