buttons-cabinet = 🧰 Кабінет виконавця

messages-executor-cabinet =
    🧰 <b>Кабінет виконавця</b>
    Псевдонім: { $alias }
    Статус: { $status }
    Одночасно замовлень: { $limit }
    Відсоток: { $percent }

    Допуски:
    { $permissions }
messages-executor-no_permissions = поки немає, зверніться до адміністратора
messages-executor-status_on = приймає замовлення
messages-executor-status_off = вимкнено
messages-executor-percent_service = за сервісом
messages-executor-no_profile = Профіль виконавця не знайдено.

messages-executor-admin_done = Готово.
messages-executor-usage_add = Використання: /executor_add &lt;tg_id&gt; &lt;псевдонім&gt;
messages-executor-usage_perm = Використання: /executor_perm &lt;tg_id&gt; &lt;код сервісу&gt; &lt;RU,UA,...&gt;. Замість країн «-» знімає допуск.
messages-executor-usage_switch = Використання: /executor_on або /executor_off &lt;tg_id&gt;
messages-executor-usage_limits = Використання: /executor_limits &lt;tg_id&gt; &lt;паралельних&gt; [відсоток]
messages-executor-err_alias_taken = Такий псевдонім уже зайнятий.
messages-executor-err_exists = Цей користувач уже виконавець.
messages-executor-err_not_found = Виконавця не знайдено.
messages-executor-err_service = Сервіс з таким кодом не знайдено.
messages-executor-err_country = Однієї з країн немає в довіднику.
messages-executor-err_input = Недопустиме значення. Псевдонім: 2-32 символи без пробілів, відсоток 0-100.

units-hours = { $n } год
units-minutes = { $n } хв

messages-card =
    📦 <b>Замовлення № { $id }</b>
    { $product }
    { $place }
    💵 Ви отримаєте { $earning }
    ⏱ Термін до { $deadline }

    <blockquote>{ $fields }</blockquote>
messages-card-file = (файл)

buttons-take = ✅ Взяти
buttons-refuse = ✖️ Відмовитися

messages-executor-offer =
    🆕 <b>Нове замовлення</b>

    { $card }
messages-executor-assigned =
    📌 <b>Вам призначено замовлення</b>

    { $card }
messages-executor-taken = ✅ Замовлення № { $id } за вами. Якщо не встигаєте, відмовтеся: воно повернеться в чергу.
messages-executor-take_failed = Замовлення № { $id } уже недоступне: його взяв інший виконавець, або немає допуску чи вільного місця.
messages-executor-refused = Ви відмовилися від замовлення № { $id }.
messages-executor-refuse_failed = Замовлення № { $id } уже не можна повернути в чергу.
messages-executor-offer_taken = Замовлення № { $id } узяв інший виконавець.
messages-executor-offer_cancelled = Замовлення № { $id } скасовано покупцем.
messages-executor-overdue = ⏱ Термін замовлення № { $id } минув, воно повернулося в чергу.
messages-executor-no_executor = Для замовлення № { $id } немає відповідного виконавця.
