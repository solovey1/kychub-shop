messages-purchase-head = 🧾 <b>{ $product }</b>, { $details }
messages-purchase-line_done = ✅ { $label }: { $value }
messages-purchase-line_now = ✏️ <b>{ $label }</b>
messages-purchase-line_next = ▫️ { $label }
messages-purchase-line_next_optional = ▫️ { $label } (optional)
messages-purchase-ask = Enter { $label }
messages-purchase-choose = Choose { $label }
messages-purchase-hint_file = 📎 Send a photo or a file
messages-purchase-files_value =
    📎 { $n ->
        [one] { $n } file
       *[other] { $n } files
    }
messages-purchase-hint_files = 📎 Send photos or files, up to { $max }
messages-purchase-files_progress = 📎 Files: { $n } of { $max }
messages-purchase-prompt = ✏️ { $label }
messages-purchase-invalid = ⚠️ { $reason }
messages-purchase-confirm_title = 🧾 <b>Check your order</b>
messages-purchase-line_price = 💵 Price: { $amount }
messages-purchase-line_discount = 🎟 Discount { $code }: −{ $amount }
messages-purchase-line_total = <b>Total: { $total }</b>, balance { $balance }
messages-purchase-line_missing = ⚠️ Short by { $amount }
messages-purchase-promo_error = ⚠️ Promo code not applied: { $reason }
messages-purchase-promo_ask = 🎟 Send the promo code in one message.
messages-purchase-edit_pick = ✏️ What to change?
messages-purchase-cancelled = ✖️ Order cancelled.
messages-purchase-accepted =
    ✅ <b>Order #{ $id } is paid</b>

    { $next }
messages-purchase-next_done = The result comes in the next message.
messages-purchase-next_queue = Looking for an executor.
messages-purchase-next_work = Already in progress.
messages-purchase-done = 🎉 <b>Order #{ $id } is complete</b>
messages-purchase-reason_required = an answer is required.
messages-purchase-reason_too_long = the value is too long.
messages-purchase-reason_email = this does not look like an email address.
messages-purchase-reason_number = a number is expected.
messages-purchase-reason_choice = pick one of the options with a button.
messages-purchase-reason_format = the value does not match the expected format.
messages-purchase-reason_control = remove control characters.
messages-purchase-reason_not_file = a file or a photo is expected.
messages-purchase-reason_not_text = text is expected.
messages-purchase-expired = The order session has expired. Open the product again.
messages-purchase-out_of_stock = This item is out of stock. You have not been charged.
messages-purchase-unavailable = This product is unavailable. You have not been charged.
messages-purchase-done_file = The result is attached.
messages-purchase-admin_manual =
    New manual order #{ $id }
    Buyer: { $user }
    Product: { $product }
    { $answers }

messages-promo-reason_not_found = no such code, or it is disabled.
messages-promo-reason_expired = the code has expired.
messages-promo-reason_exhausted = the code has reached its usage limit.
messages-promo-reason_not_bonus = this is not a bonus code.
messages-promo-reason_bonus_code = this is a bonus code, activate it in "Balance".
messages-promo-reason_wrong_product = the code does not apply to this product.
messages-promo-reason_min_amount = the order total is below the minimum for this code.
messages-promo-reason_not_allowed = this code is not available to you.
messages-promo-reason_new_users_only = the code is for new customers only.
messages-promo-reason_already_used = you have already used this code.

buttons-pay = ✅ Pay { $amount }
buttons-promo = 🎟 Promo code
buttons-skip = ⏭ Skip
buttons-copy = 📋 Copy
buttons-topup = 💳 Top up
buttons-topup_missing = 💳 Top up { $amount }
buttons-edit = ✏️ Edit details
buttons-new_account = ➕ New details
buttons-done = ✅ Done

messages-purchase-line_online = 🟢 Executors online: { $count }
messages-purchase-line_offline = 🌙 Everyone is offline right now — your order will be picked up as soon as someone shows up
messages-purchase-how_it_works =
    ℹ️ <b>How it works</b>
    💰 Your money waits in reserve → 🧑‍💻 an executor does the job → ✅ you check and confirm. Something wrong? 🆘 Support is one tap away.

messages-purchase-pick_account =
    👤 <b>Which account is this for?</b>
    { $product }
    I will reuse the details from your earlier orders, no retyping 🙌
messages-purchase-account_from = Account from order #{ $id } ({ $date })
