buttons-tip = 💝 Leave a tip
buttons-tip_custom = Other amount
buttons-balance_short = 💰 Balance
buttons-rating = ⭐ Rating
buttons-payout_wallet = Payout wallet
buttons-withdraw = Withdraw
buttons-wallet_set = Set address

messages-feedback-ask = ⭐ Order #{ $id } is done. How was the executor's work? Rate it from 1 to 5.
messages-feedback-rated = ✅ Thank you, your rating of { $score } for order #{ $id } is saved.
messages-feedback-already_rated = This order is already rated.
messages-feedback-unavailable = The order is not available for rating or tips.
messages-feedback-tip_choose = A tip for the executor of order #{ $id }. Choose an amount, it is taken from your balance.
messages-feedback-tip_ask = Enter the tip in dollars, for example 2.50.
messages-feedback-tip_invalid = Could not read the amount. It must be above zero, at most 1000, with at most two decimal places.
messages-feedback-tipped = 💝 Done, { $amount } was sent to the executor. Thank you.
messages-feedback-tip_funds = Your balance is too low for this tip.
messages-feedback-tip_done = The tip for this screen was already sent.

messages-executor-tip = 💝 You received a tip of { $amount } for order #{ $id }.


messages-executor-rating =
    ⭐ <b>Rating</b>
    Completed: { $completed }
    Failed: { $failed }
    Overdue: { $overdue }
    Refusals: { $refused }
    Average time, min: { $minutes }
    Average score: { $score }
messages-executor-balance =
    💰 <b>Executor balance</b>
    💵 Available: { $available }
    { $holds }
    Withdrawals from { $minimum }

    Latest operations:
    { $history }
messages-executor-hold_line = 🔒 { $amount } becomes available on { $date }
messages-executor-hold_none = 🔒 Nothing in hold
messages-executor-wallet =
    👛 <b>Payout wallet</b>
    <code>{ $address }</code>
messages-executor-wallet_empty = No payout wallet set.
messages-executor-wallet_ask = Send the wallet address in one message: no spaces, up to 128 characters.
messages-executor-wallet_invalid = This address does not fit: no spaces and at most 128 characters.
messages-executor-wallet_saved = Wallet saved.
messages-executor-wallet_missing = Set a payout wallet first.
messages-executor-below_minimum = You need at least { $minimum } available to withdraw.
messages-executor-withdrawal_created = ✅ Withdrawal request for { $amount } created. An administrator will make the payout.

messages-withdrawal-new =
    💸 Withdrawal request #{ $id }
    Executor: { $user }
    Amount: { $amount }
    Address: <code>{ $address }</code>
