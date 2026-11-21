# FarmHub Shop — Фаза 7: API для Mini App

> Executor: Sonnet. Читать вместе с `2026-11-21-farmhub-shop.md` (Global Constraints) и spec §11, §15a.

**Goal:** HTTP API и WebSocket на существующем FastAPI для Mini App: покупатель (заказы, баланс, чаты заказа),
исполнитель (очередь, свои заказы, результат, баланс, кошелёк, вывод, рейтинг), менеджер/админ (тикеты, чаты,
подтверждение заказов). Админка каталога и прочее — фаза 9.

**Тесты не пишем.** Проверка: ruff, mypy (2 известные ошибки), `import app.__main__`, dishka-граф, плюс запуск
`uvicorn` с фейковыми env (без БД) и `GET /openapi.json` — схема строится без ошибок.

## Решения

- Всё под префиксом `/api`, роутеры в `app/presentation/fastapi/api/{auth,me,orders,chat,executor,staff}.py`,
  схемы ответов (pydantic) в `app/presentation/fastapi/api/schemas.py`. Подключить в `setup_fastapi`.
- **Авторизация без сессий:** каждый запрос несёт `Authorization: tma <initData>`. Проверка —
  `aiogram.utils.web_app.safe_parse_webapp_init_data(token, init_data)`; `auth_date` не старше 24 ч; иначе 401.
  Зависимость `current_user` → `User` из `UsersGateway` (нет в базе → 401). Роли — `require_role(Role.X)` → 403.
  Пользователь с `blocked_at` не блокируется (это «заблокировал бота», не бан).
- Обращение к интеракторам — через dishka (`FromDishka`, `@inject`), как в healthcheck. Ошибки приложения
  маппятся одним exception handler: `OrderUnavailable`/`*NotFound` → 404, `InsufficientFunds`/`InvalidAmount`/
  `InvalidInput`/`PromoError` → 422 с `{"code": ...}`, `AppError` → 400.
- **Эндпоинты** (JSON; деньги — строкой `"12.50"`; время — ISO UTC):
  - `GET /api/me` — id, name, language, roles (список строк), balance, для исполнителя — hold/available.
  - Покупатель: `GET /api/orders?page=` , `GET /api/orders/{id}` (snapshot, статус, сумма, результат если
    `completed`, исполнитель — только `alias`), `POST /api/orders/{id}/cancel`, `GET /api/balance` (баланс +
    последние 50 проводок `main`), `GET /api/executors/mine` («мои исполнители»).
  - Чаты: `POST /api/orders/{id}/chat` → id переписки заказа (`order_conversation(actor_id, ...)`),
    `POST /api/support` (`{order_id?}`) → id переписки тикета, `GET /api/conversations/{id}/messages?before_id=&limit=50`,
    `POST /api/conversations/{id}/messages` (`{text}` до 4000 символов). Доступ — только `can_post`/участник;
    чужая переписка → 404. Отправка из Mini App: сохранить `Message`, доставить в Telegram текстом через Relay
    (нужен путь «без исходного сообщения»: `send_message` с заголовком).
  - Файлы: `GET /api/files/{message_id}` — отдаёт медиа сообщения (бот скачивает по `file_id`, стримит); доступ —
    участник переписки этого сообщения. Загрузку файлов из Mini App не делаем.
  - Исполнитель (`EXECUTOR`): `GET /api/executor/queue` (заказы `in_queue`, где он в `eligible`; поля как в
    уведомлении), `POST /api/executor/orders/{id}/take`, `GET /api/executor/orders`, `GET /api/executor/orders/{id}`
    (анкета без `hidden_from_executor`, схема результата), `POST .../refuse`, `POST .../result` (`{fields: {key: value}}`,
    файлы не поддерживаются), `GET /api/executor/stats`, `GET /api/executor/balance`, `PUT /api/executor/wallet`,
    `POST /api/executor/withdraw`.
  - Персонал (`MANAGER`|`ADMIN`): `GET /api/tickets?scope=open|mine|all` (all — только ADMIN),
    `POST /api/tickets/{id}/take`, `POST /api/tickets/{id}/close`, `GET /api/staff/orders?status=ready`,
    `GET /api/staff/orders/{id}`, `POST /api/staff/orders/{id}/confirm`, `.../send_back` (`{comment}`), `.../fail`.
  После успешных действий — те же Telegram-уведомления, что делает бот (переиспользовать flows/сервисы
  уведомлений, не дублировать тексты).
- **Анонимность:** ни один ответ API исполнителю не содержит id, имени или username покупателя.
- **WebSocket** `GET /api/ws?auth=<urlencoded initData>`: та же проверка. Внутрипроцессный `EventHub`
  (APP-scope: `dict[user_id, set[WebSocket]]`). События `{"type": "message", "conversation_id", "message": {...}}`,
  `{"type": "order", "order_id", "status"}`, `{"type": "queue"}` (изменилась очередь исполнителя),
  `{"type": "ticket", "ticket_id", "status"}`. Публикуют Relay/уведомители после commit. Пинг клиента раз в 30 с.
  ponytail: хаб в памяти одного процесса — при нескольких репликах заменить на Redis pub/sub.
- **Раздача фронтенда:** если существует каталог `webapp/dist`, смонтировать `StaticFiles(html=True)` на `/app`.
  URL Mini App = `SERVER_URL + "/app/"`. Бот ставит кнопку меню (`set_chat_menu_button` с `WebAppInfo`) на старте,
  если `SERVER_URL` начинается с `https://`.

## Review Focus

1. Чужой `order_id`/`conversation_id`/`ticket_id`/`message_id` → 404, не 403 и не данные.
2. Просроченный (>24 ч) или подделанный `initData` → 401; WebSocket закрывается с кодом 4401.
3. Исполнитель получает анкету и чат без данных покупателя.
4. Исполнитель без допуска видит пустую очередь и не может взять заказ через API.
5. Двойной `POST .../take` / `.../confirm` → второй получает 409/404, деньги не задвоены (интеракторы уже защищены).

## Задачи и коммиты

1. `feat(api): init-data auth, error mapping, me/orders/balance endpoints`.
2. `feat(api): chat endpoints, file proxy, websocket hub`.
3. `feat(api): executor and staff endpoints, static web app and menu button`.
