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
