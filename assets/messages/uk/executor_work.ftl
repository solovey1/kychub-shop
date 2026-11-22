buttons-my_orders = 📦 Мої замовлення
buttons-submit_result = 📤 Здати результат
buttons-confirm = ✅ Підтвердити
buttons-send_back = ↩️ Повернути виконавцю
buttons-fail = ❌ Провал і повернення
buttons-fail_confirm = Так, повернути гроші покупцю
buttons-open = Відкрити

messages-executor-orders_title = <b>Мої замовлення</b>
messages-executor-orders_empty = Замовлень поки немає.
messages-executor-order =
    { $card }

    Статус: { $status }
messages-executor-until = Здати до: { $time } UTC
messages-executor-order_missing = Замовлення № { $id } не знайдено.
messages-executor-result_ask =
    <b>Результат за замовленням № { $id }</b>
    Питання { $step } з { $total }
    { $label }
messages-executor-deadline_passed = ⏱ Термін замовлення № { $id } вийшов, результат не прийнято. Замовлення повернеться в чергу.
messages-executor-result_invalid = Результат за замовленням № { $id } не пройшов перевірку. Почніть здачу заново.
messages-executor-submitted = 📤 Результат за замовленням № { $id } надіслано на перевірку.
messages-executor-confirmed = ✅ Замовлення № { $id } підтверджено. Нарахування надійшло в холд.
messages-executor-sent_back =
    ↩️ Замовлення № { $id } повернуто на доопрацювання.
    Коментар: { $comment }
messages-executor-order_closed = Замовлення № { $id } закрито адміністрацією, нарахування за ним скасовано.

messages-review-missing = Замовлення № { $id } не знайдено.
messages-review-unavailable = Замовлення № { $id } уже оброблене або недоступне для цієї дії.
messages-review-confirmed = ✅ Замовлення підтверджено, результат надіслано покупцю.
messages-review-sent_back = Замовлення № { $id } повернуто виконавцю.
messages-review-failed = ❌ Замовлення № { $id } закрито, гроші повернуто покупцю.
messages-review-status = Статус: { $status }
messages-review-result =
    Результат:
    <code>{ $result }</code>
messages-review-files = Файлів: { $count }
messages-review-ask_comment = Напишіть коментар для виконавця за замовленням № { $id } одним повідомленням.
messages-review-fail_confirm = Закрити замовлення № { $id } як невиконане й повернути гроші покупцю? Нарахування виконавцю буде скасовано, якщо холд ще не знято.

messages-order-refunded = ↩️ Замовлення № { $id } не виконано. На баланс повернуто { $amount }.

buttons-cancel_order = 🚫 Скасувати замовлення
buttons-cancel_confirm = 🚫 Так, скасувати
messages-orders-cancel_confirm = 🚫 Скасувати замовлення № { $id }? Гроші повністю повернуться на баланс.
messages-orders-cancelled = 🚫 Замовлення № { $id } скасовано. На баланс повернуто { $amount }.
messages-executor-reminder = ⏰ Замовлення №{ $id }: лишилося { $left }, здати до { $time }
buttons-open_order = 📦 Відкрити замовлення
buttons-ext_ask = ⏳ Попросити продовження
messages-executor-ext_pick = ⏳ На скільки продовжити замовлення №{ $id }? Покупець має погодитись.
messages-executor-ext_waiting = ⏳ Прохання продовжити на { $duration } чекає на відповідь покупця.
messages-executor-ext_failed = Зараз не можна просити продовження замовлення №{ $id }: прохання вже надіслано, ліміт вичерпано або термін минув.
messages-executor-extended = ✅ Замовлення №{ $id }: покупець продовжив термін до { $time }
messages-executor-ext_declined = ✖️ Замовлення №{ $id }: покупець не продовжив термін, здати до { $time }
