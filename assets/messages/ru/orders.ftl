messages-orders-title = 📦 <b>Мои заказы</b>
messages-orders-empty = У вас пока нет заказов.
messages-orders-not_found = Заказ не найден.
messages-order =
    📦 <b>Заказ №{ $id }</b>
    { $product }, { $variant }
    💵 Сумма: { $total }{ $held }

    { $steps }{ $executor }
messages-order-held = 🔒 { $amount } зарезервировано, спишется после выполнения
messages-order-step_done = ✅ { $name }, { $time }
messages-order-step_done_notime = ✅ { $name }
messages-order-step_now = ⚙️ { $name }
messages-order-step_until = ⚙️ { $name }, сдаст до { $time }
messages-order-step_next = ▫️ { $name }
messages-order-step_final = { $name }, { $time }
messages-order-executor = 👤 Исполнитель: { $alias }

order-step-paid = Оплачен
order-step-in_queue = В очереди
order-step-assigned = В работе
order-step-ready = На проверке
order-step-completed = Выполнен
order-step-failed = ❌ Не выполнен
order-step-refunded = ↩️ Возвращён
order-step-cancelled = 🚫 Отменён

order-icon-awaiting_input = 🧾
order-icon-paid = 💵
order-icon-in_queue = 🕓
order-icon-assigned = ⚙️
order-icon-ready = 🔍
order-icon-completed = ✅
order-icon-failed = ❌
order-icon-refunded = ↩️
order-icon-cancelled = 🚫

order-status-awaiting_input = { order-icon-awaiting_input } ожидает данных
order-status-paid = { order-icon-paid } оплачен
order-status-in_queue = { order-icon-in_queue } в очереди
order-status-assigned = { order-icon-assigned } в работе
order-status-ready = { order-icon-ready } на проверке
order-status-completed = { order-icon-completed } выполнен
order-status-failed = { order-icon-failed } не выполнен
order-status-refunded = { order-icon-refunded } возвращён
order-status-cancelled = { order-icon-cancelled } отменён

buttons-order_item = { $icon } №{ $id }, { $title }, { $total }
buttons-open_order = 📦 Открыть заказ
