messages-orders-title = 📦 <b>My orders</b>
messages-orders-empty = You have no orders yet.
messages-orders-not_found = Order not found.
messages-order =
    📦 <b>Order #{ $id }</b>
    { $product }, { $variant }
    💵 Total: { $total }{ $held }

    { $steps }{ $executor }
messages-order-held = 🔒 { $amount } reserved, charged once the order is done
messages-order-step_done = ✅ { $name }, { $time }
messages-order-step_done_notime = ✅ { $name }
messages-order-step_now = ⚙️ { $name }
messages-order-step_until = ⚙️ { $name }, due by { $time }
messages-order-step_next = ▫️ { $name }
messages-order-step_final = { $name }, { $time }
messages-order-executor = 👤 Executor: { $alias }

order-step-paid = Paid
order-step-in_queue = In queue
order-step-assigned = In progress
order-step-ready = Under review
order-step-completed = Completed
order-step-failed = ❌ Failed
order-step-refunded = ↩️ Refunded
order-step-cancelled = 🚫 Cancelled

order-icon-awaiting_input = 🧾
order-icon-paid = 💵
order-icon-in_queue = 🕓
order-icon-assigned = ⚙️
order-icon-ready = 🔍
order-icon-completed = ✅
order-icon-failed = ❌
order-icon-refunded = ↩️
order-icon-cancelled = 🚫

order-status-awaiting_input = { order-icon-awaiting_input } awaiting input
order-status-paid = { order-icon-paid } paid
order-status-in_queue = { order-icon-in_queue } in queue
order-status-assigned = { order-icon-assigned } in progress
order-status-ready = { order-icon-ready } under review
order-status-completed = { order-icon-completed } completed
order-status-failed = { order-icon-failed } failed
order-status-refunded = { order-icon-refunded } refunded
order-status-cancelled = { order-icon-cancelled } cancelled

buttons-order_item = { $icon } #{ $id }, { $title }, { $total }
buttons-open_order = 📦 Open order
messages-order-extension = ⏳ The executor asks for { $duration } more. New deadline: { $time }
messages-order-extension_ask = ⏳ The executor asks to extend order #{ $id } by { $duration }. New deadline: { $time }
messages-order-extension_yes = ✅ The deadline of order #{ $id } is extended to { $time }
messages-order-extension_no = ✖️ You declined the extension of order #{ $id }. The deadline is unchanged.
messages-order-extension_stale = This request is no longer relevant
buttons-ext_yes = ✅ Extend
buttons-ext_no = ✖️ No
