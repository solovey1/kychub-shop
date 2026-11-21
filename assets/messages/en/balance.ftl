messages-balance =
    <b>Balance: { $amount }</b>

    Recent activity:
    { $history }
messages-balance-entry = { $date } · { $kind } · { $amount }
messages-balance-history_empty = No activity yet.
messages-balance-credited = { $amount } has been added to your balance.
messages-balance-debited = { $amount } has been deducted from your balance.

messages-topup-choose = Choose a top-up amount.
messages-topup-disabled = Top-ups will be available soon.
messages-topup-custom_ask = Enter the amount in dollars, for example 12.50.
messages-topup-invalid = Could not read the amount. It must be a number above zero, up to 1000.
messages-topup-done = Balance topped up by { $amount }.
messages-redeem-ask = Send the promo code in one message.
messages-redeem-done = Promo code activated, { $amount } credited.
messages-redeem-error = Promo code not activated: { $reason }

messages-admin-topup_usage = Usage: /topup ID AMOUNT comment. A negative amount debits.
messages-admin-topup_done = Done: { $amount } for user { $user_id }. Balance: { $balance }.
messages-admin-topup_failed = Failed: the user was not found, the amount is zero, or the balance would go negative.

ledger-kind-topup = Top-up
ledger-kind-purchase = Purchase
ledger-kind-refund = Refund
ledger-kind-executor_earning = Executor earning
ledger-kind-earning_reversal = Earning reversal
ledger-kind-hold_release = Hold release
ledger-kind-tip = Tip
ledger-kind-withdrawal = Withdrawal
ledger-kind-promo_bonus = Promo bonus
ledger-kind-admin_adjust = Adjustment

buttons-redeem = Redeem promo code
buttons-topup_custom = Other amount
