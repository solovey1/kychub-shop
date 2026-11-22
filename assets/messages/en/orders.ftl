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
order-step-ready = Check the result
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
buttons-deal_ok = ✅ All good
messages-order-ready =
    🎉 The executor has finished order #{ $id }. Check the result in the order.
    If all is well, tap «All good». Otherwise the order confirms itself on { $time }.
messages-order-confirm_reminder = ⏳ Order #{ $id } will confirm itself on { $time }. Please check the result.
messages-order-check =
    🔍 <b>Result</b>
    { $result }
    📎 Files: { $files }

    All in order? Tap «All good». Otherwise the order confirms itself on { $time }.
messages-order-confirmed = ✅ Order #{ $id } confirmed. Thank you!
buttons-deal_ask = 🆘 Call support
buttons-deal_skip = No reason
buttons-dispute_open = 🆘 Open the dispute
dispute-who-buyer = the buyer
dispute-who-executor = the executor
dispute-from-buyer = the buyer
dispute-from-executor = the executor
dispute-from-you = you
messages-order-dispute = 🆘 <b>Dispute open.</b> Support is looking into it.
messages-order-dispute_wait = 🆘 <b>Dispute open.</b> Waiting for an answer from { $who } until { $time }.
messages-dispute-ask_reason = 🆘 Order #{ $id }: describe the problem in one line, or tap «No reason».
messages-dispute-opened = 🆘 The dispute on order #{ $id } is open. Support will join. The other side has to answer in the chat until { $time }.
messages-dispute-cancelled = Fine, no dispute was opened.
messages-dispute-staff = 🆘 Dispute on order #{ $id }. Opened by { $who }.
messages-dispute-reply = 🆘 A dispute is open on order #{ $id }. Answer in the chat until { $time }, or it will be decided against you.
messages-dispute-reply_requested = 🆘 Support asks you to answer about order #{ $id } in the chat until { $time }.
messages-dispute-reminder = ⏰ Dispute on order #{ $id }: { $left } left. Answer in the chat until { $time }.
messages-dispute-closed = ✅ The dispute on order #{ $id } is closed, the order goes on.
buttons-order_open = 📦 Open the order
messages-contacts-staff = ⚠️ { $who } keeps trying to pass contacts in order #{ $id }.

messages-order-waiting = ⏳ <b>Order #{ $id } is in the queue</b>: all executors are busy. Someone will take it as soon as they are free.
buttons-cancel_refund = ✖️ Cancel and refund

buttons-cancel_ask = ↩️ Ask to cancel
messages-order-cancel_wait = ↩️ You asked to cancel the order. The executor answers by { $time }, otherwise it is cancelled on its own and your money is returned.
messages-order-cancel_asked = ↩️ Your request to cancel order #{ $id } went to the executor. If they agree or stay silent for an hour, the money returns to your balance.
messages-order-cancel_unavailable = You cannot ask to cancel right now: a request is already sent, the limit is spent or the order is no longer in work.
messages-order-cancel_agreed = ↩️ Order #{ $id } is cancelled, { $amount } is back on your balance.
messages-order-cancel_declined = The executor keeps working on order #{ $id }. If something is wrong — 🆘 call support.
