messages-balance =
    💰 <b>Баланс: { $amount }</b>

    Последние операции:
    { $history }
messages-balance-entry = { $kind } · { $date } · { $amount }
messages-balance-history_empty = Операций пока нет.
messages-balance-credited = ➕ На ваш баланс зачислено { $amount }.
messages-balance-debited = ➖ С вашего баланса списано { $amount }.

messages-topup-choose = Выберите сумму пополнения.
messages-topup-disabled = Пополнение скоро будет доступно.
messages-topup-custom_ask = Введите сумму в долларах, например 12.50.
messages-topup-invalid = Не удалось распознать сумму. Введите число от { $min } до { $max } не более чем с двумя знаками после точки.
messages-topup-done = ✅ Баланс пополнен на { $amount }.
messages-topup-method = Пополнение на { $amount }. Выберите способ оплаты.
messages-topup-invoice = Оплатите { $amount } кнопкой ниже. Счёт действует 1 час. Баланс пополнится автоматически, либо нажмите «Проверить оплату».
messages-topup-binance =
    Отправьте { $amount } в USDT через Binance Pay в течение 1 часа.

    Pay ID: <code>{ $pay_id }</code>
    Примечание: <code>{ $note }</code>

    Примечание должно совпадать точно, иначе платёж не будет найден. Затем нажмите «Проверить оплату».
messages-topup-status_created = Оплата пока не поступила. Если вы уже оплатили, подождите минуту и проверьте снова.
messages-topup-status_pending = Платёж подтверждается. Обычно это занимает несколько минут.
messages-topup-status_partially_paid = Получена сумма меньше запрошенной, поэтому баланс не пополнен. Обратитесь в поддержку.
messages-topup-status_canceled = Счёт истёк или отменён. Создайте новый.
messages-topup-gateway_error = Платёжный сервис не отвечает. Попробуйте позже.
messages-redeem-ask = Введите промокод одним сообщением.
messages-redeem-done = ✅ Промокод активирован, начислено { $amount }.
messages-redeem-error = Промокод не активирован: { $reason }

messages-admin-topup_usage = Использование: /topup ID СУММА комментарий. Отрицательная сумма списывает.
messages-admin-topup_done = Готово: { $amount } пользователю { $user_id }. Баланс: { $balance }.
messages-admin-topup_failed = Не получилось: пользователь не найден, сумма нулевая или баланс стал бы отрицательным.

ledger-kind-topup = ➕ Пополнение
ledger-kind-purchase = ➖ Покупка
ledger-kind-refund = ↩️ Возврат
ledger-kind-executor_earning = Начисление исполнителю
ledger-kind-earning_reversal = Отмена начисления
ledger-kind-hold_release = Выплата из холда
ledger-kind-tip = 💝 Чаевые
ledger-kind-withdrawal = Вывод
ledger-kind-promo_bonus = 🎁 Бонус по промокоду
ledger-kind-admin_adjust = Корректировка

buttons-redeem = 🎟 Активировать промокод
buttons-topup_custom = Другая сумма
buttons-pay_invoice = 💳 Оплатить
buttons-check_payment = 🔄 Проверить оплату
buttons-copy_pay_id = Копировать Pay ID
buttons-copy_note = Копировать примечание
buttons-provider_cryptobot = CryptoBot
buttons-provider_binance = Binance Pay
buttons-provider_nowpayments = NOWPayments
buttons-provider_test = Тестовый платёж
