messages-balance =
    <b>Баланс: { $amount }</b>

    Останні операції:
    { $history }
messages-balance-entry = { $date } · { $kind } · { $amount }
messages-balance-history_empty = Операцій поки немає.
messages-balance-credited = На ваш баланс зараховано { $amount }.
messages-balance-debited = З вашого балансу списано { $amount }.

messages-topup-choose = Оберіть суму поповнення.
messages-topup-disabled = Поповнення скоро буде доступне.
messages-topup-custom_ask = Введіть суму в доларах, наприклад 12.50.
messages-topup-invalid = Не вдалося розпізнати суму. Потрібне число більше нуля, не більше 1000.
messages-topup-done = Баланс поповнено на { $amount }.
messages-redeem-ask = Введіть промокод одним повідомленням.
messages-redeem-done = Промокод активовано, нараховано { $amount }.
messages-redeem-error = Промокод не активовано: { $reason }

messages-admin-topup_usage = Використання: /topup ID СУМА коментар. Від'ємна сума списує.
messages-admin-topup_done = Готово: { $amount } користувачу { $user_id }. Баланс: { $balance }.
messages-admin-topup_failed = Не вдалося: користувача не знайдено, сума нульова або баланс став би від'ємним.

ledger-kind-topup = Поповнення
ledger-kind-purchase = Покупка
ledger-kind-refund = Повернення
ledger-kind-executor_earning = Нарахування виконавцю
ledger-kind-earning_reversal = Скасування нарахування
ledger-kind-hold_release = Виплата з холду
ledger-kind-tip = Чайові
ledger-kind-withdrawal = Виведення
ledger-kind-promo_bonus = Бонус за промокодом
ledger-kind-admin_adjust = Коригування

buttons-redeem = Активувати промокод
buttons-topup_custom = Інша сума
