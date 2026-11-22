messages-balance =
    💰 <b>Balance: { $amount }</b>

    Recent activity:
    { $history }
messages-balance-entry = { $kind } · { $date } · { $amount }
messages-balance-history_empty = No activity yet.
messages-balance-credited = ➕ { $amount } has been added to your balance.
messages-balance-debited = ➖ { $amount } has been deducted from your balance.

messages-topup-choose = Choose a top-up amount.
messages-topup-disabled = Top-ups will be available soon.
messages-topup-custom_ask = Enter the amount in dollars, for example 12.50.
messages-topup-invalid = Could not read the amount. Enter a number from { $min } to { $max } with at most two decimal places.
messages-topup-done = ✅ Balance topped up by { $amount }.
messages-topup-method = Top-up { $amount }. Choose a payment method.
messages-topup-invoice = Pay { $amount } with the button below. The invoice is valid for 1 hour. The balance is topped up automatically, or press "Check payment".
messages-topup-binance =
    Send { $amount } in USDT via Binance Pay within 1 hour.

    Pay ID: <code>{ $pay_id }</code>
    Note: <code>{ $note }</code>

    The note must match exactly, otherwise the payment will not be found. Then press "Check payment".
messages-topup-status_created = Payment not received yet. If you have already paid, wait a minute and try again.
messages-topup-status_pending = The payment is being confirmed. This usually takes a few minutes.
messages-topup-status_partially_paid = The amount received is less than requested, so the balance has not been topped up. Contact support.
messages-topup-status_canceled = The invoice has expired or was canceled. Create a new one.
messages-topup-gateway_error = The payment service is not responding. Try again later.
messages-redeem-ask = Send the promo code in one message.
messages-redeem-done = ✅ Promo code activated, { $amount } credited.
messages-redeem-error = Promo code not activated: { $reason }

messages-admin-topup_usage = Usage: /topup ID AMOUNT comment. A negative amount debits.
messages-admin-topup_done = Done: { $amount } for user { $user_id }. Balance: { $balance }.
messages-admin-topup_failed = Failed: the user was not found, the amount is zero, or the balance would go negative.

ledger-kind-topup = ➕ Top-up
ledger-kind-purchase = ➖ Purchase
ledger-kind-refund = ↩️ Refund
ledger-kind-executor_earning = Executor earning
ledger-kind-earning_reversal = Earning reversal
ledger-kind-hold_release = Hold release
ledger-kind-tip = 💝 Tip
ledger-kind-withdrawal = Withdrawal
ledger-kind-promo_bonus = 🎁 Promo bonus
ledger-kind-admin_adjust = Adjustment

buttons-redeem = 🎟 Redeem promo code
buttons-topup_custom = Other amount
buttons-pay_invoice = 💳 Pay
buttons-check_payment = 🔄 Check payment
buttons-copy_pay_id = Copy Pay ID
buttons-copy_note = Copy note
buttons-provider_cryptobot = CryptoBot
buttons-provider_binance = Binance Pay
buttons-provider_nowpayments = NOWPayments
buttons-provider_test = Test payment
