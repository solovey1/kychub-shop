buttons-cabinet = 🧰 Кабинет исполнителя

messages-executor-cabinet =
    🧰 <b>Кабинет исполнителя</b>
    Псевдоним: { $alias }
    Статус: { $status }
    Одновременно заказов: { $limit }
    Процент: { $percent }

    Допуски:
    { $permissions }
messages-executor-no_permissions = пока нет, обратитесь к администратору
messages-executor-status_on = принимает заказы
messages-executor-status_off = отключён
messages-executor-percent_service = по сервису
messages-executor-no_profile = Профиль исполнителя не найден.

messages-executor-admin_done = Готово.
messages-executor-usage_add = Использование: /executor_add &lt;tg_id&gt; &lt;псевдоним&gt;
messages-executor-usage_perm = Использование: /executor_perm &lt;tg_id&gt; &lt;код сервиса&gt; &lt;RU,UA,...&gt;. Вместо стран «-» снимает допуск.
messages-executor-usage_switch = Использование: /executor_on или /executor_off &lt;tg_id&gt;
messages-executor-usage_limits = Использование: /executor_limits &lt;tg_id&gt; &lt;параллельных&gt; [процент]
messages-executor-err_alias_taken = Такой псевдоним уже занят.
messages-executor-err_exists = Этот пользователь уже исполнитель.
messages-executor-err_not_found = Исполнитель не найден.
messages-executor-err_service = Сервис с таким кодом не найден.
messages-executor-err_country = Одной из стран нет в справочнике.
messages-executor-err_input = Недопустимое значение. Псевдоним: 2-32 символа без пробелов, процент 0-100.

units-hours = { $n } ч
units-minutes = { $n } мин

messages-card =
    📦 <b>Заказ № { $id }</b>
    { $product }
    { $place }
    💵 Вы получите { $earning }
    ⏱ Срок до { $deadline }

    <blockquote>{ $fields }</blockquote>
messages-card-file = (файл)

buttons-take = ✅ Взять
buttons-refuse = ✖️ Отказаться

messages-executor-offer =
    🆕 <b>Новый заказ</b>

    { $card }
messages-executor-assigned =
    📌 <b>Вам назначен заказ</b>

    { $card }
messages-executor-taken = ✅ Заказ № { $id } взят. Если не успеваете, откажитесь: он вернётся в очередь.
messages-executor-take_failed = Заказ № { $id } уже недоступен: его взял другой исполнитель, либо нет допуска или свободного места.
messages-executor-refused = Вы отказались от заказа № { $id }.
messages-executor-refuse_failed = Заказ № { $id } уже нельзя вернуть в очередь.
messages-executor-offer_taken = Заказ № { $id } взят другим исполнителем.
messages-executor-offer_cancelled = Заказ № { $id } отменён покупателем.
messages-executor-overdue = ⏱ Срок заказа № { $id } истёк, заказ вернулся в очередь.
messages-executor-no_executor = Для заказа № { $id } нет подходящего исполнителя.
