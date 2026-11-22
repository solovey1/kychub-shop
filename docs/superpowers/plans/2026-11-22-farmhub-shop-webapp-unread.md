# FarmHub Shop — навигация и непрочитанные в Mini App

> Executor: Sonnet. Читать с `2026-11-21-farmhub-shop.md`, `-phase7.md`, `-phase8.md`, `-support-in-app.md`.

**Goal:** из любого экрана, в том числе открытого кнопкой из бота, видна навигация приложения; у вкладок и
строк списков — счётчики непрочитанного.

**Тесты не пишем.** Проверка: ruff, mypy (2 известные ошибки), `alembic upgrade head` → `downgrade -1` →
`upgrade head` на dev-базе (`.env`, Postgres localhost:15432), `alembic check` без изменений, `npm run build`,
скриншоты в моках (375 px): вкладки со счётчиками, чат, открытый по `?to=`.

## Навигация

- Нижние вкладки видны на всех экранах. На экране чата поле ввода стоит над вкладками; клавиатура открыта —
  вкладки прячутся (`viewportHeight < viewportStableHeight - 100`), чтобы не съедать место.
- `BackButton` на вложенных экранах: если в истории приложения есть куда вернуться — `history.back()`; если
  экран открыт по `?to=` (первая запись истории) — на родителя: `/chat/*` и `/orders/:id/chat/*` →
  `/orders`, `/ticket/*` → `/support/tickets`, `/work/order/:id/chat/*` → `/work/order/:id`.
  Признак «первая запись» — флаг в модуле, выставленный при обработке `?to=`.

## Непрочитанные

- **БД, миграция `005_conversation_reads.py`** (вручную): таблица `conversation_reads`:
  `conversation_id` FK → conversations ON DELETE CASCADE, `user_id` FK → users ON DELETE CASCADE,
  `last_read_message_id BIGINT NOT NULL DEFAULT 0`, `updated_at timestamptz NOT NULL DEFAULT now()`,
  PK `(conversation_id, user_id)`. Индекс `messages(conversation_id, id)` (вместо одиночного
  `ix_messages_conversation_id`, если он становится лишним — удалить в той же миграции). Модель в
  `app/domain/support.py`.
- Непрочитанное сообщение для пользователя: в переписке, которую он может читать (`reader_role`), `id >
  last_read_message_id` и `sender_id != user_id`. Считать одним SQL на список переписок (LEFT JOIN
  conversation_reads, COUNT FILTER), не в цикле.
- **Отметка прочитанного:** `POST /api/conversations/{id}/read` `{message_id}` → upsert с
  `GREATEST(old, new)`; чужая переписка → 404. Клиент вызывает, когда показал последнее сообщение (открыл чат,
  пришло новое сообщение в открытый чат). Отправка своего сообщения — тоже прочитано до него (на сервере в
  `post`).
- **API:**
  - `GET /api/unread` → `{orders, support, work, tickets, review}`, все `int`:
    `orders` — заказы покупателя с непрочитанным в чате заказа; `support` — его тикеты с непрочитанным;
    `work` — заказы исполнителя с непрочитанным; `tickets` — для персонала тикеты (open без менеджера + свои)
    с непрочитанным; `review` — заказы `ready` (ждут проверки). Ролей нет — 0.
  - В списках поле `unread: int`: `OrderBrief` (чат заказа), `ExecutorOrderListItem`, `TicketOut`. В `MeOut`
    — ничего, счётчики только через `/unread`.
- **Клиент:** хук `useUnread()` — `/api/unread` при старте, при каждом live-событии `message`, `order`,
  `ticket`, `queue` (debounce 500 мс) и после `read`. Вкладки: «Заказы» = `orders + support`, «Работа» =
  `work`, «Поддержка» = `tickets + review`. Сегменты внутри: «Тикеты» = `tickets`, «Проверка» = `review`,
  «Мои» = `work`. Строки списков: точка цвета `--btn` и число справа, если `unread > 0`; кнопка поддержки
  на экране заказов покупателя — с числом `support`.
- Значок: круг 18 px, `--btn` фон, `--btn-fg` текст, 11 px, `99+` при переполнении. Без анимации.
- Моки (`src/dev/mock.ts`): `/unread` и поля `unread` в фикстурах, чтобы счётчики были видны.

## Review Focus

1. Счётчик не включает свои сообщения и сообщения в переписках, которые пользователь читать не может.
2. Чужой `conversation_id` в `/read` → 404, отметка не пишется.
3. `last_read_message_id` не откатывается назад при запоздалом запросе.
4. Счёт одним запросом на список, без N+1.
5. Кнопка «назад» в чате, открытом из бота, ведёт на родительский экран, а не закрывает приложение.

## Коммиты

1. `feat(db): conversation reads (migration 005)`.
2. `feat(api): unread counters and read marks`.
3. `feat(webapp): navigation on every screen, unread badges`.
