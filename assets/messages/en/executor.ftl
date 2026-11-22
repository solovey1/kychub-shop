buttons-cabinet = 🧰 Executor desk

messages-executor-cabinet =
    🧰 <b>Executor desk</b>
    { $online }
    Alias: { $alias }
    Status: { $status }
    Orders at once: { $limit }
    Percent: { $percent }

    Permissions:
    { $permissions }
messages-executor-online_on = 🟢 Online — orders are coming
messages-executor-online_off = ⚪️ Offline — no orders
messages-executor-no_permissions = none yet, ask an administrator
messages-executor-status_on = accepting orders
messages-executor-status_off = switched off
messages-executor-percent_service = by service
messages-executor-no_profile = Executor profile not found.

messages-executor-admin_done = Done.
messages-executor-usage_add = Usage: /executor_add &lt;tg_id&gt; [alias]. Without an alias a random name is picked.
messages-executor-usage_perm = Usage: /executor_perm &lt;tg_id&gt; &lt;service code&gt; &lt;RU,UA,...&gt;. Use "-" instead of countries to revoke.
messages-executor-usage_switch = Usage: /executor_on or /executor_off &lt;tg_id&gt;
messages-executor-usage_limits = Usage: /executor_limits &lt;tg_id&gt; &lt;parallel&gt; [percent]
messages-executor-err_alias_taken = This alias is already taken.
messages-executor-err_exists = This user is already an executor.
messages-executor-err_not_found = Executor not found.
messages-executor-err_service = No service with this code.
messages-executor-err_country = One of the countries is not in the directory.
messages-executor-err_input = Invalid value. Alias: 2-32 characters without spaces, percent 0-100.

units-hours = { $n } h
units-minutes = { $n } min

messages-card =
    📦 <b>Order #{ $id }</b>
    { $product }
    { $place }
    💵 You get { $earning }
    ⏱ Due in { $deadline }

    <blockquote>{ $fields }</blockquote>
messages-card-file =
    { $n ->
        [one] ({ $n } file)
       *[other] ({ $n } files)
    }

buttons-take = ✅ Take
buttons-refuse = ✖️ Refuse

messages-executor-offer =
    🆕 <b>New order</b>

    { $card }
messages-executor-assigned =
    📌 <b>An order is assigned to you</b>

    { $card }
messages-executor-taken = ✅ Order #{ $id } is yours. If you cannot make it, refuse: it goes back to the queue.
messages-executor-take_failed = Order #{ $id } is no longer available: another executor took it, or you have no permission or free slot.
messages-executor-refused = You refused order #{ $id }.
messages-executor-refuse_failed = Order #{ $id } can no longer be returned to the queue.
messages-executor-offer_taken = Order #{ $id } was taken by another executor.
messages-executor-offer_cancelled = Order #{ $id } was cancelled by the buyer.
messages-executor-overdue = ⏱ The deadline of order #{ $id } has passed, it went back to the queue.
messages-executor-no_executor = No suitable executor for order #{ $id }.

buttons-go_offline = ⚪️ Go offline
buttons-go_online = 🟢 Go online

messages-executor-assigned_accept =
    📌 <b>An order is assigned to you</b>

    { $card }

    ⏳ Confirm that you take it by { $time }. The time to do it starts after you confirm.
messages-executor-accepted = ✅ Order #{ $id } accepted. The clock is running, good luck!
messages-executor-accept_failed = Order #{ $id } can no longer be accepted: time is up or it went to someone else.
messages-executor-ignored = 🌙 You did not accept order #{ $id } — we set your status to «offline». Turn it on when you are ready.
messages-executor-accept_wait = ⏳ Confirm that you take the order by { $time }.
buttons-accept = ✅ I take it

messages-executor-welcome =
    👋 <b>You are online — a quick tour</b>

    📥 An order arrives as a card: tap ✅ Take, first come first served. If an order was assigned to you, confirm it with ✅ I take it within a few minutes, or it goes to someone else.
    ⏰ Every order has a deadline. Running late? Ask for an extension, the buyer has to agree.
    ❓ Missing data? Tap "Need data": the deadline pauses until the buyer answers.
    💰 Your earnings sit in hold first and become available a few days after the buyer confirms.
    🚫 No contacts, links or messengers: talk only in the order chat.
