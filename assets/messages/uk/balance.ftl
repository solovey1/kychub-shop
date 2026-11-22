messages-balance =
    💰 <b>Баланс: { $amount }</b>{ $held }

    Останні операції:
    { $history }
messages-held = 🔒 У замовленнях: { $amount }
messages-balance-entry = { $kind } · { $date } · { $amount }
messages-balance-history_empty = Операцій поки немає.
messages-balance-credited = ➕ На ваш баланс зараховано { $amount }.
messages-balance-debited = ➖ З вашого балансу списано { $amount }.

messages-topup-choose = Оберіть суму поповнення.
messages-topup-disabled = Поповнення скоро буде доступне.
messages-topup-custom_ask = Введіть суму в доларах, наприклад 12.50.
messages-topup-invalid = Не вдалося розпізнати суму. Введіть число від { $min } до { $max } не більше ніж із двома знаками після крапки.
messages-topup-done = ✅ Баланс поповнено на { $amount }.
messages-topup-method = Поповнення на { $amount }. Оберіть спосіб оплати.
messages-topup-invoice = Сплатіть { $amount } кнопкою нижче. Рахунок діє 1 годину. Баланс поповниться автоматично, або натисніть «Перевірити оплату».
messages-topup-binance =
    Надішліть { $amount } в USDT через Binance Pay протягом 1 години.

    Pay ID: <code>{ $pay_id }</code>
    Примітка: <code>{ $note }</code>

    Примітка має збігатися точно, інакше платіж не буде знайдено. Потім натисніть «Перевірити оплату».
messages-topup-status_created = Оплата ще не надійшла. Якщо ви вже сплатили, зачекайте хвилину й перевірте знову.
messages-topup-status_pending = Платіж підтверджується. Зазвичай це займає кілька хвилин.
messages-topup-status_partially_paid = Отримано суму меншу за запитану, тому баланс не поповнено. Зверніться до підтримки.
messages-topup-status_canceled = Рахунок закінчився або скасований. Створіть новий.
messages-topup-gateway_error = Платіжний сервіс не відповідає. Спробуйте пізніше.
messages-redeem-ask = Введіть промокод одним повідомленням.
messages-redeem-done = ✅ Промокод активовано, нараховано { $amount }.
messages-redeem-error = Промокод не активовано: { $reason }

messages-admin-topup_usage = Використання: /topup ID СУМА коментар. Від'ємна сума списує.
messages-admin-topup_done = Готово: { $amount } користувачу { $user_id }. Баланс: { $balance }.
messages-admin-topup_failed = Не вдалося: користувача не знайдено, сума нульова або баланс став би від'ємним.

ledger-kind-topup = ➕ Поповнення
ledger-kind-purchase = ➖ Покупка
ledger-kind-refund = ↩️ Повернення
ledger-kind-executor_earning = Нарахування виконавцю
ledger-kind-earning_reversal = Скасування нарахування
ledger-kind-hold_release = Виплата з холду
ledger-kind-tip = 💝 Чайові
ledger-kind-withdrawal = Виведення
ledger-kind-promo_bonus = 🎁 Бонус за промокодом
ledger-kind-admin_adjust = Коригування

buttons-redeem = 🎟 Активувати промокод
buttons-topup_custom = Інша сума
buttons-pay_invoice = 💳 Сплатити
buttons-check_payment = 🔄 Перевірити оплату
buttons-copy_pay_id = Копіювати Pay ID
buttons-copy_note = Копіювати примітку
buttons-provider_cryptobot = CryptoBot
buttons-provider_binance = Binance Pay
buttons-provider_nowpayments = NOWPayments
buttons-provider_test = Тестовий платіж
ledger-kind-order_hold = 🔒 Резерв під замовлення
ledger-kind-order_capture = ✅ Списано за виконане замовлення
ledger-kind-order_release = ↩️ Резерв повернено
