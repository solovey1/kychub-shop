buttons-tip = Оставить чаевые
buttons-tip_custom = Другая сумма
buttons-balance_short = Баланс
buttons-rating = Рейтинг
buttons-payout_wallet = Кошелёк для выплат
buttons-withdraw = Вывести
buttons-wallet_set = Указать адрес

messages-feedback-ask = Заказ № { $id } выполнен. Как вам работа исполнителя? Оцените от 1 до 5.
messages-feedback-rated = Спасибо, оценка { $score } для заказа № { $id } сохранена.
messages-feedback-already_rated = Этот заказ уже оценён.
messages-feedback-unavailable = Заказ недоступен для оценки или чаевых.
messages-feedback-tip_choose = Чаевые исполнителю по заказу № { $id }. Выберите сумму, она спишется с баланса.
messages-feedback-tip_ask = Введите сумму чаевых в долларах, например 2.50.
messages-feedback-tip_invalid = Не удалось распознать сумму. Нужно число больше нуля, не больше 1000, не более двух знаков после точки.
messages-feedback-tipped = Готово, исполнителю отправлено { $amount }. Спасибо.
messages-feedback-tip_funds = На балансе не хватает средств для чаевых.
messages-feedback-tip_done = Чаевые за этот экран уже отправлены.

messages-executor-tip = Вам оставили чаевые { $amount } по заказу № { $id }.


messages-executor-rating =
    <b>Рейтинг</b>
    Выполнено: { $completed }
    Не выполнено: { $failed }
    Просрочено: { $overdue }
    Отказов: { $refused }
    Среднее время, мин: { $minutes }
    Средняя оценка: { $score }
messages-executor-balance =
    <b>Баланс исполнителя</b>
    В холде: { $hold }
    Доступно: { $available }
    Минимум для вывода: { $minimum }

    Последние операции:
    { $history }
messages-executor-wallet =
    <b>Кошелёк для выплат</b>
    <code>{ $address }</code>
messages-executor-wallet_empty = Кошелёк для выплат не указан.
messages-executor-wallet_ask = Отправьте адрес кошелька одним сообщением: без пробелов, до 128 символов.
messages-executor-wallet_invalid = Адрес не подходит: он должен быть без пробелов и не длиннее 128 символов.
messages-executor-wallet_saved = Кошелёк сохранён.
messages-executor-wallet_missing = Сначала укажите кошелёк для выплат.
messages-executor-below_minimum = Для вывода нужно не меньше { $minimum } на доступном балансе.
messages-executor-withdrawal_created = Заявка на вывод { $amount } создана. Выплату проведёт администратор.

messages-withdrawal-new =
    Заявка на вывод № { $id }
    Исполнитель: { $user }
    Сумма: { $amount }
    Адрес: <code>{ $address }</code>
