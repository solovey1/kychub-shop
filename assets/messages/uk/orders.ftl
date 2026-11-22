messages-orders-title = 📦 <b>Мої замовлення</b>
messages-orders-empty = У вас поки немає замовлень.
messages-orders-not_found = Замовлення не знайдено.
messages-order =
    📦 <b>Замовлення №{ $id }</b>
    { $product }, { $variant }
    💵 Сума: { $total }{ $held }

    { $steps }{ $executor }
messages-order-held = 🔒 { $amount } зарезервовано, спишеться після виконання
messages-order-step_done = ✅ { $name }, { $time }
messages-order-step_done_notime = ✅ { $name }
messages-order-step_now = ⚙️ { $name }
messages-order-step_until = ⚙️ { $name }, здасть до { $time }
messages-order-step_next = ▫️ { $name }
messages-order-step_final = { $name }, { $time }
messages-order-executor = 👤 Виконавець: { $alias }

order-step-paid = Оплачено
order-step-in_queue = У черзі
order-step-assigned = У роботі
order-step-ready = Перевірте результат
order-step-completed = Виконано
order-step-failed = ❌ Не виконано
order-step-refunded = ↩️ Повернуто
order-step-cancelled = 🚫 Скасовано

order-icon-awaiting_input = 🧾
order-icon-paid = 💵
order-icon-in_queue = 🕓
order-icon-assigned = ⚙️
order-icon-ready = 🔍
order-icon-completed = ✅
order-icon-failed = ❌
order-icon-refunded = ↩️
order-icon-cancelled = 🚫

order-status-awaiting_input = { order-icon-awaiting_input } очікує даних
order-status-paid = { order-icon-paid } оплачено
order-status-in_queue = { order-icon-in_queue } у черзі
order-status-assigned = { order-icon-assigned } у роботі
order-status-ready = { order-icon-ready } на перевірці
order-status-completed = { order-icon-completed } виконано
order-status-failed = { order-icon-failed } не виконано
order-status-refunded = { order-icon-refunded } повернуто
order-status-cancelled = { order-icon-cancelled } скасовано

buttons-order_item = { $icon } №{ $id }, { $title }, { $total }
buttons-open_order = 📦 Відкрити замовлення
messages-order-extension = ⏳ Виконавець просить продовжити термін на { $duration }. Новий термін: до { $time }
messages-order-extension_ask = ⏳ Виконавець просить продовжити замовлення №{ $id } на { $duration }. Новий термін: до { $time }
messages-order-extension_yes = ✅ Термін замовлення №{ $id } продовжено до { $time }
messages-order-extension_no = ✖️ Ви відмовили в продовженні замовлення №{ $id }. Термін не змінився.
messages-order-extension_stale = Прохання вже неактуальне
buttons-ext_yes = ✅ Продовжити
buttons-ext_no = ✖️ Ні
buttons-deal_ok = ✅ Все гаразд
messages-order-ready =
    🎉 Виконавець завершив замовлення №{ $id }. Перевірте результат у замовленні.
    Якщо все добре — натисніть «Все гаразд». Інакше замовлення підтвердиться автоматично { $time }.
messages-order-confirm_reminder = ⏳ Замовлення №{ $id } підтвердиться автоматично { $time }. Перевірте результат.
messages-order-check =
    🔍 <b>Результат</b>
    { $result }
    📎 Файлів: { $files }

    Усе гаразд? Натисніть «Все гаразд». Інакше замовлення підтвердиться автоматично { $time }.
messages-order-confirmed = ✅ Замовлення №{ $id } підтверджено. Дякуємо!
buttons-deal_ask = 🆘 Покликати підтримку
buttons-deal_skip = Без причини
buttons-dispute_open = 🆘 Відкрити спір
dispute-who-buyer = покупець
dispute-who-executor = виконавець
dispute-from-buyer = покупця
dispute-from-executor = виконавця
dispute-from-you = вас
messages-order-dispute = 🆘 <b>Спір відкрито.</b> Підтримка розбирається.
messages-order-dispute_wait = 🆘 <b>Спір відкрито.</b> Чекаємо відповіді від { $who } до { $time }.
messages-dispute-ask_reason = 🆘 Замовлення №{ $id }: опишіть проблему одним рядком або натисніть «Без причини».
messages-dispute-opened = 🆘 Спір щодо замовлення №{ $id } відкрито. Підключиться підтримка. Друга сторона має відповісти в чаті до { $time }.
messages-dispute-cancelled = Добре, спір не відкрито.
messages-dispute-staff = 🆘 Спір щодо замовлення №{ $id }. Відкрив: { $who }.
messages-dispute-reply = 🆘 За замовленням №{ $id } відкрито спір. Відповідайте в чаті до { $time }, інакше спір вирішиться не на вашу користь.
messages-dispute-reply_requested = 🆘 Підтримка просить відповісти щодо замовлення №{ $id } у чаті до { $time }.
messages-dispute-reminder = ⏰ Спір щодо замовлення №{ $id }: залишилось { $left }. Відповідайте в чаті до { $time }.
messages-dispute-closed = ✅ Спір щодо замовлення №{ $id } закрито, замовлення продовжується.
