buttons-tip = 💝 Залишити чайові
buttons-tip_custom = Інша сума
buttons-balance_short = 💰 Баланс
buttons-rating = ⭐ Рейтинг
buttons-payout_wallet = Гаманець для виплат
buttons-withdraw = Вивести
buttons-wallet_set = Вказати адресу

messages-feedback-ask = ⭐ Замовлення № { $id } виконано. Як вам робота виконавця? Оцініть від 1 до 5.
messages-feedback-rated = ✅ Дякуємо, оцінку { $score } для замовлення № { $id } збережено.
messages-feedback-already_rated = Це замовлення вже оцінене.
messages-feedback-unavailable = Замовлення недоступне для оцінки чи чайових.
messages-feedback-tip_choose = Чайові виконавцю за замовленням № { $id }. Оберіть суму, вона спишеться з балансу.
messages-feedback-tip_ask = Введіть суму чайових у доларах, наприклад 2.50.
messages-feedback-tip_invalid = Не вдалося розпізнати суму. Потрібне число більше нуля, не більше 1000, не більш ніж два знаки після крапки.
messages-feedback-tipped = 💝 Готово, виконавцю надіслано { $amount }. Дякуємо.
messages-feedback-tip_funds = На балансі не вистачає коштів для чайових.
messages-feedback-tip_done = Чайові з цього екрана вже надіслано.

messages-executor-tip = 💝 Вам залишили чайові { $amount } за замовленням № { $id }.


messages-executor-rating =
    ⭐ <b>Рейтинг</b>
    Виконано: { $completed }
    Не виконано: { $failed }
    Прострочено: { $overdue }
    Відмов: { $refused }
    Середній час, хв: { $minutes }
    Середня оцінка: { $score }
messages-executor-balance =
    💰 <b>Баланс виконавця</b>
    💵 Доступно: { $available }
    { $holds }
    Виведення від { $minimum }

    Останні операції:
    { $history }
messages-executor-hold_line = 🔒 { $amount } стане доступним { $date }
messages-executor-hold_none = 🔒 У холді нічого немає
messages-executor-wallet =
    👛 <b>Гаманець для виплат</b>
    <code>{ $address }</code>
messages-executor-wallet_empty = Гаманець для виплат не вказано.
messages-executor-wallet_ask = Надішліть адресу гаманця одним повідомленням: без пробілів, до 128 символів.
messages-executor-wallet_invalid = Адреса не підходить: вона має бути без пробілів і не довшою за 128 символів.
messages-executor-wallet_saved = Гаманець збережено.
messages-executor-wallet_missing = Спочатку вкажіть гаманець для виплат.
messages-executor-below_minimum = Для виводу потрібно не менше { $minimum } на доступному балансі.
messages-executor-withdrawal_created = ✅ Заявку на вивід { $amount } створено. Виплату проведе адміністратор.

messages-withdrawal-new =
    💸 Заявка на вивід № { $id }
    Виконавець: { $user }
    Сума: { $amount }
    Адреса: <code>{ $address }</code>
