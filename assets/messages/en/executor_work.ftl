buttons-my_orders = 📦 My orders
buttons-submit_result = 📤 Submit result
buttons-confirm = ✅ Confirm
buttons-send_back = ↩️ Send back
buttons-fail = ❌ Fail and refund
buttons-fail_confirm = Yes, refund the buyer
buttons-open = Open

messages-executor-orders_title = <b>My orders</b>
messages-executor-orders_empty = No orders yet.
messages-executor-order =
    { $card }

    Status: { $status }
messages-executor-until = Submit by: { $time } UTC
messages-executor-order_missing = Order #{ $id } not found.
messages-executor-result_ask =
    <b>Result for order #{ $id }</b>
    Question { $step } of { $total }
    { $label }
messages-executor-deadline_passed = ⏱ The deadline of order #{ $id } has passed, the result was not accepted. The order goes back to the queue.
messages-executor-result_invalid = The result for order #{ $id } did not pass validation. Start again.
messages-executor-submitted = 📤 The result for order #{ $id } was sent for review.
messages-executor-confirmed = ✅ Order #{ $id } is confirmed. The payout is now on hold.
messages-executor-sent_back =
    ↩️ Order #{ $id } was sent back for rework.
    Comment: { $comment }
messages-executor-order_closed = Order #{ $id } was closed by the administration, its payout was cancelled.

messages-review-missing = Order #{ $id } not found.
messages-review-unavailable = Order #{ $id } was already handled or does not allow this action.
messages-review-confirmed = ✅ The order is confirmed, the result was sent to the buyer.
messages-review-sent_back = Order #{ $id } was sent back to the executor.
messages-review-failed = ❌ Order #{ $id } is closed, the buyer was refunded.
messages-review-status = Status: { $status }
messages-review-result =
    Result:
    <code>{ $result }</code>
messages-review-files = Files: { $count }
messages-review-ask_comment = Write a comment for the executor of order #{ $id } in one message.
messages-review-fail_confirm = Close order #{ $id } as failed and refund the buyer? The executor payout is cancelled if the hold is still on.

messages-order-refunded = ↩️ Order #{ $id } could not be completed. { $amount } was returned to your balance.

buttons-cancel_order = 🚫 Cancel order
buttons-cancel_confirm = 🚫 Yes, cancel
messages-orders-cancel_confirm = 🚫 Cancel order #{ $id }? The full amount returns to your balance.
messages-orders-cancelled = 🚫 Order #{ $id } is cancelled. { $amount } was returned to your balance.
messages-executor-reminder = ⏰ Order #{ $id }: { $left } left, deliver by { $time }
buttons-open_order = 📦 Open order
buttons-ext_ask = ⏳ Ask for more time
messages-executor-ext_pick = ⏳ How much more time for order #{ $id }? The buyer has to agree.
messages-executor-ext_waiting = ⏳ Your request for { $duration } more is waiting for the buyer.
messages-executor-ext_failed = You cannot ask for more time on order #{ $id } right now: a request is already open, the limit is spent or the deadline has passed.
messages-executor-extended = ✅ Order #{ $id }: the buyer extended the deadline to { $time }
messages-executor-ext_declined = ✖️ Order #{ $id }: the buyer did not extend, deliver by { $time }
