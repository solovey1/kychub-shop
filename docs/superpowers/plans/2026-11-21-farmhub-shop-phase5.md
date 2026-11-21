# FarmHub Shop — Фаза 5: исполнители

> Executor: Sonnet. Читать вместе с `2026-11-21-farmhub-shop.md` (Global Constraints) и spec §5, §8, §15a, §15b.

**Goal:** заказы с выдачей `executor` уходят исполнителям с допуском (сервис + страна), в очередь или
автоназначением; исполнитель берёт, сдаёт результат («Готово»); админ/менеджер подтверждает; исполнителю
начисляется процент в холд, после холда — в доступные; возвраты, отмены, просрочки, оценки, чаевые, рейтинг,
заявка на вывод (заглушка).

**Рабочее место исполнителя в этой фазе — бот** (тонкий UI поверх interactors). Mini App (фаза 8) переиспользует
те же interactors. Переписка покупатель ↔ исполнитель — фаза 6.

**Тесты не пишем.** Проверка: ruff, mypy (2 известные ошибки), `import app.__main__`, dishka-граф (одноразовый скрипт).

## Общие правила фазы

- Любая смена статуса заказа: `OrdersGateway.get_for_update(order_id)` (`SELECT ... FOR UPDATE`) → проверки →
  `ensure_transition` → `OrderEvent` → проводки → один `commit()`. Уведомления — только после commit.
- Деньги исполнителя: процент = `percent_override` профиля, иначе `service.executor_percent`; база — оплачено
  `price - discount`; `percent_of`. Проводки с `ref=f"order:{order.id}"` (ключ идемпотентности включает счёт).
- Настройки: `SettingsGateway.get(key, default)` поверх таблицы `settings`. Ключи и значения по умолчанию:
  `hold_days=3`, `review_delay_hours=2`, `min_withdrawal="10.00"`. Константы-ключи в `app/application/settings_keys.py`.
- Уведомления в Telegram — один модуль `app/infrastructure/telegram/notifier.py` (`Notifier`: `send(user_id, key,
  reply_markup=None, **kwargs) -> Message | None` на языке получателя, ошибки Telegram логирует и глотает,
  `edit(chat_id, message_id, key, **kwargs)`). Перевести на него `_notify` из `scheduler/payments.py`.
- Кому уведомления «на подтверждение»: всем пользователям с ролью `ADMIN` или `MANAGER`, в личку.
- Новые задачи планировщика регистрируются в `app/infrastructure/scheduler/__init__.py`, по образцу `payments.py`.

## Review Focus

1. Два исполнителя жмут «Взять» одновременно → заказ получает ровно один, второму «уже взят».
2. «Взять» без допуска (сервис/страна) или сверх `max_parallel_orders` → отказ, даже если кнопка осталась у него в чате.
3. Возврат после подтверждения, пока холд не снят → начисление сторнируется ровно один раз; после снятия холда —
   не сторнируется, баланс исполнителя не уходит в минус.
4. Снятие холда запущено дважды (задача + повтор) → деньги переведены один раз.
5. Срок истёк ровно в момент сдачи результата → либо сдача прошла, либо заказ вернулся в очередь; не оба.

---

### Task 5.1: Настройки, регистрация исполнителей, уведомитель

- `SettingsGateway` + репозиторий; `Notifier` (см. выше).
- `ExecutorAdminInteractor`:
  - `register(admin_id, tg_id: int, alias: str) -> ExecutorProfile` — если пользователя нет: создать `User(id=tg_id,
    name="", language="ru")`; `roles |= EXECUTOR`; профиль (alias уникален → понятная ошибка). `AuditLog`.
  - `set_permissions(admin_id, tg_id, service_code: str, countries: list[str])` — заменить допуски по сервису.
  - `set_active(admin_id, tg_id, active: bool)`, `set_limits(admin_id, tg_id, max_parallel: int | None,
    percent_override: int | None)`.
- `provide_user`: если `user.name == ""` (заготовка админа) — заполнить имя из Telegram при первом апдейте.
- Админ-команды (личка, `HasRole(ADMIN)`): `/executor_add <tg_id> <alias>`, `/executor_perm <tg_id> <service_code>
  <CC,CC,...>`, `/executor_off <tg_id>`, `/executor_on <tg_id>`, `/executor_limits <tg_id> <max_parallel> [percent]`.
  Ответ — краткое подтверждение или ошибка.
- В главном меню у пользователя с ролью `EXECUTOR` — кнопка «Кабинет исполнителя» → экран: «Мои заказы»,
  «Баланс», «Рейтинг», «Кошелёк для выплат».

Commit: `feat(executors): settings, executor registration, notifier`.

### Task 5.2: Распределение заказов

- `DispatchInteractor`:
  - `eligible(order_id) -> list[int]` — активные исполнители с допуском `(product.service_id, variant.country_code)`
    и нагрузкой (`assigned` + `ready`) меньше `max_parallel_orders`; исключить тех, у кого по этому заказу есть
    событие `refused` или `overdue`.
  - `dispatch(order_id) -> DispatchResult` — режим `service.assign_mode`:
    `queue` → вернуть список `eligible` для рассылки предложения; `auto` → выбрать по наименьшей нагрузке, при
    равенстве — больше выполненных заказов, и назначить (как `take`). Нет кандидатов → ничего, событие
    `no_executor`, уведомить админов один раз.
  - `take(executor_id, order_id) -> bool` — под блокировкой заказа: статус `in_queue`, `executor_id IS NULL`,
    исполнитель в `eligible` → `assigned`, `assigned_at`, `deadline_at = now + service.deadline_minutes`.
  - `refuse(executor_id, order_id)` — только свой `assigned` → `in_queue`, `executor_id = NULL`, событие `refused`,
    затем `dispatch` заново.
  - `expire_overdue() -> list[int]` — `assigned` с `deadline_at < now` → `in_queue`, событие `overdue`
    (с id исполнителя), повторный `dispatch`.
  - `requeue_stale() -> list[int]` — `in_queue` без исполнителя дольше 10 минут без нового `dispatch` → повтор
    (появился допущенный исполнитель).
- Вызов `dispatch` — из flow покупки после commit для `executor`-заказов и из задач планировщика.
- Предложение исполнителю (queue): №, сервис, флаг страны, сколько он получит, срок, поля анкеты без
  `hidden_from_executor`. Кнопка «Взять» (`success`). id отправленных сообщений хранить в Redis
  (`StorageKey` `OrderOfferKey(order_id)` → список `[chat_id, message_id]`, TTL 1 сутки); после `take` остальным
  отредактировать текст на «Заказ взят другим исполнителем», кнопку убрать.
- Auto: исполнителю — уведомление «Вам назначен заказ» с кнопкой «Отказаться» (`danger`).
- Планировщик: `expire_overdue` раз в 60 с, `requeue_stale` раз в 5 мин. Исполнителю при просрочке — уведомление.

Commit: `feat(executors): queue and auto dispatch, take, refuse, overdue`.

### Task 5.3: Результат, подтверждение, деньги, холд

- `FulfillmentWorkInteractor` (исполнитель):
  - `my_orders(executor_id, page)`, `get(executor_id, order_id)` — только свои. Анкета без скрытых полей.
    Имя/username/id покупателя исполнителю не показывать никогда.
  - `submit(executor_id, order_id, result: dict[str, str]) -> Order` — свой `assigned`, `deadline_at` не прошёл;
    проверка по `product.result_schema` (`FormSchema`; пустая схема = одно текстовое поле `result`);
    `order.result = result`, `assigned → ready`, `ready_at`. После commit — уведомить подтверждающих.
- `OrderReviewInteractor` (админ/менеджер, `HasRole(ADMIN) | HasRole(MANAGER)`):
  - `confirm(actor_id, order_id)` — `ready → completed`, `completed_at`, `hold_until = now + hold_days`,
    `review_due_at = now + review_delay_hours`; проводка `executor_hold +earning` (`executor_earning`).
    После commit — выдать результат покупателю (как в фазе 3: `<code>`, `copy_text` ≤256, файл >3500).
  - `send_back(actor_id, order_id, comment)` — `ready → assigned`, новый `deadline_at`, событие с комментарием,
    уведомить исполнителя.
  - `fail_and_refund(actor_id, order_id, reason)` — из `paid|in_queue|assigned|ready` → `failed → refunded`;
    из `completed` → `refunded`. Покупателю `main +(price - discount)` (`refund`, `ref=f"order:{id}"`).
    Если был `executor_earning` и холд ещё не снят (нет `hold_release` по заказу) → `executor_hold -earning`
    (`earning_reversal`). Уведомить покупателя и исполнителя.
- Покупатель: `cancel(user_id, order_id)` — только свой `in_queue` → `cancelled` + возврат (как выше). Кнопка
  «Отменить заказ» на экране заказа только в этом статусе.
- `HoldInteractor.release_due() -> list[int]` — `completed`, `hold_until <= now`, есть `executor_earning` без
  `hold_release`: две проводки `hold_release` (`executor_hold -earning`, `executor_available +earning`), обе
  `ref=f"order:{id}"`. Каждый заказ — своя транзакция. Планировщик: раз в 10 мин.
- Экраны: подтверждающему — карточка заказа с анкетой и результатом, кнопки «Подтвердить» (`success`),
  «Вернуть исполнителю», «Провал и возврат» (`danger`, с подтверждением). Исполнителю — «Сдать результат»
  (пошагово по `result_schema`, как анкета фазы 3; тип `file` — `file_id`) и «Отказаться».

Commit: `feat(executors): result submission, confirmation, refunds and hold release`.

### Task 5.4: Оценки, чаевые, рейтинг, вывод

- Планировщик раз в 5 мин: `completed`, `review_due_at <= now`, нет события `review_requested` → покупателю
  сообщение «Оцените заказ №N»: кнопки 1–5 и «Оставить чаевые»; событие `review_requested`.
- `ReviewInteractor.rate(user_id, order_id, score: int)` — заказ свой, `completed`, есть `executor_id`;
  `user_id`/`executor_id` берутся из заказа; повторная оценка → «уже оценено».
- `TipInteractor.tip(user_id, order_id, amount: Decimal, token: str)` — заказ свой и `completed`; одна транзакция:
  `main -amount` и `executor_available +amount` (`tip`, обе `ref=f"tip:{token}"`). Чаевые сразу доступны
  (не холдятся) — решение разработчика: холд нужен для возвратов, а чаевые не возвращаются. Суммы-кнопки
  $1 / $3 / $5 / своя.
- `ExecutorStats.stats(executor_id) -> Stats(completed, failed, overdue, refused, avg_minutes, avg_score)` по заказам,
  событиям и оценкам. Исполнитель видит в «Рейтинг». Кеш не нужен.
- Покупатель: в «Мои заказы» кнопка «Мои исполнители» — список `alias` и сколько заказов каждый выполнил для него.
- Вывод (заглушка, spec §15b): «Кошелёк для выплат» — исполнитель вводит адрес (строка до 128 символов,
  без пробелов) → `payout_wallet`. «Вывести» — вся сумма `executor_available`, не меньше `min_withdrawal`,
  кошелёк задан: `Withdrawal(pending, address)` + `executor_available -amount` (`withdrawal`,
  `ref=f"withdrawal:{id}"`), уведомить админов. Отправка денег не делается.
- Баланс исполнителя: «В холде $X», «Доступно $Y», последние 10 проводок по его счетам.

Commit: `feat(executors): reviews, tips, rating, withdrawal requests`.
