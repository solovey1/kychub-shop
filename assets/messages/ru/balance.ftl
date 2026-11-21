messages-balance =
    <b>Баланс: { $amount }</b>

    Последние операции:
    { $history }
messages-balance-entry = { $date } · { $kind } · { $amount }
messages-balance-history_empty = Операций пока нет.
messages-balance-credited = На ваш баланс зачислено { $amount }.
messages-balance-debited = С вашего баланса списано { $amount }.

messages-topup-choose = Выберите сумму пополнения.
messages-topup-disabled = Пополнение скоро будет доступно.
messages-topup-custom_ask = Введите сумму в долларах, например 12.50.
messages-topup-invalid = Не удалось распознать сумму. Нужно число больше нуля, не более 1000.
messages-topup-done = Баланс пополнен на { $amount }.
messages-redeem-ask = Введите промокод одним сообщением.
messages-redeem-done = Промокод активирован, начислено { $amount }.
messages-redeem-error = Промокод не активирован: { $reason }

messages-admin-topup_usage = Использование: /topup ID СУММА комментарий. Отрицательная сумма списывает.
messages-admin-topup_done = Готово: { $amount } пользователю { $user_id }. Баланс: { $balance }.
messages-admin-topup_failed = Не получилось: пользователь не найден, сумма нулевая или баланс стал бы отрицательным.

ledger-kind-topup = Пополнение
ledger-kind-purchase = Покупка
ledger-kind-refund = Возврат
ledger-kind-executor_earning = Начисление исполнителю
ledger-kind-earning_reversal = Отмена начисления
ledger-kind-hold_release = Выплата из холда
ledger-kind-tip = Чаевые
ledger-kind-withdrawal = Вывод
ledger-kind-promo_bonus = Бонус по промокоду
ledger-kind-admin_adjust = Корректировка

buttons-redeem = Активировать промокод
buttons-topup_custom = Другая сумма
