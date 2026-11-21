buttons-cabinet = Executor desk

messages-executor-cabinet =
    <b>Executor desk</b>
    Alias: { $alias }
    Status: { $status }
    Orders at once: { $limit }
    Percent: { $percent }

    Permissions:
    { $permissions }
messages-executor-no_permissions = none yet, ask an administrator
messages-executor-status_on = accepting orders
messages-executor-status_off = switched off
messages-executor-percent_service = by service
messages-executor-no_profile = Executor profile not found.

messages-executor-admin_done = Done.
messages-executor-usage_add = Usage: /executor_add &lt;tg_id&gt; &lt;alias&gt;
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
    <b>Order #{ $id }</b>
    { $product }
    { $place }
    Executor pay: { $earning } · deadline: { $deadline }

    { $fields }
messages-card-file = (file)

buttons-take = Take
buttons-refuse = Refuse

messages-executor-offer =
    <b>New order</b>

    { $card }
messages-executor-assigned =
    <b>An order is assigned to you</b>

    { $card }
messages-executor-taken = Order #{ $id } is yours. If you cannot make it, refuse: it goes back to the queue.
messages-executor-take_failed = Order #{ $id } is no longer available: another executor took it, or you have no permission or free slot.
messages-executor-refused = You refused order #{ $id }.
messages-executor-refuse_failed = Order #{ $id } can no longer be returned to the queue.
messages-executor-offer_taken = Order #{ $id } was taken by another executor.
messages-executor-offer_cancelled = Order #{ $id } was cancelled by the buyer.
messages-executor-overdue = The deadline of order #{ $id } has passed, it went back to the queue.
messages-executor-no_executor = No suitable executor for order #{ $id }.
