buttons-my_orders = 📦 Мои заказы
buttons-submit_result = 📤 Сдать результат
buttons-confirm = ✅ Подтвердить
buttons-send_back = ↩️ Вернуть исполнителю
buttons-fail = ❌ Провал и возврат
buttons-fail_confirm = Да, вернуть деньги покупателю
buttons-open = Открыть

messages-executor-orders_title = <b>Мои заказы</b>
messages-executor-orders_empty = Заказов пока нет.
messages-executor-order =
    { $card }

    Статус: { $status }
messages-executor-until = Сдать до: { $time }
messages-executor-order_missing = Заказ № { $id } не найден.
messages-executor-result_ask =
    <b>Результат по заказу № { $id }</b>
    Вопрос { $step } из { $total }
    { $label }
messages-executor-deadline_passed = ⏱ Срок заказа № { $id } вышел, результат не принят. Заказ вернётся в очередь.
messages-executor-result_invalid = Результат по заказу № { $id } не прошёл проверку. Начните сдачу заново.
messages-executor-submitted = 📤 Результат по заказу № { $id } отправлен на проверку.
messages-executor-confirmed = ✅ Заказ № { $id } подтверждён. Начисление поступило в холд.
messages-executor-sent_back =
    ↩️ Заказ № { $id } возвращён на доработку.
    Комментарий: { $comment }
messages-executor-order_closed = Заказ № { $id } закрыт администрацией, начисление по нему отменено.

messages-review-missing = Заказ № { $id } не найден.
messages-review-unavailable = Заказ № { $id } уже обработан или недоступен для этого действия.
messages-review-confirmed = ✅ Заказ подтверждён, результат отправлен покупателю.
messages-review-sent_back = Заказ № { $id } возвращён исполнителю.
messages-review-failed = ❌ Заказ № { $id } закрыт, деньги возвращены покупателю.
messages-review-status = Статус: { $status }
messages-review-result =
    Результат:
    <code>{ $result }</code>
messages-review-files = Файлов: { $count }
messages-review-ask_comment = Напишите комментарий для исполнителя по заказу № { $id } одним сообщением.
messages-review-fail_confirm = Закрыть заказ № { $id } как невыполненный и вернуть деньги покупателю? Начисление исполнителю будет отменено, если холд ещё не снят.

messages-order-refunded = ↩️ Заказ № { $id } не выполнен. На баланс возвращено { $amount }.

buttons-cancel_order = 🚫 Отменить заказ
buttons-cancel_confirm = 🚫 Да, отменить
messages-orders-cancel_confirm = 🚫 Отменить заказ № { $id }? Деньги вернутся на баланс полностью.
messages-orders-cancelled = 🚫 Заказ № { $id } отменён. На баланс возвращено { $amount }.
messages-executor-reminder = ⏰ Заказ №{ $id }: осталось { $left }, сдать до { $time }
buttons-open_order = 📦 Открыть заказ
buttons-ext_ask = ⏳ Попросить продление
messages-executor-ext_pick = ⏳ На сколько продлить заказ №{ $id }? Покупатель должен согласиться.
messages-executor-ext_waiting = ⏳ Просьба продлить на { $duration } ждёт ответа покупателя.
messages-executor-ext_failed = Сейчас нельзя попросить продление заказа №{ $id }: просьба уже отправлена, лимит исчерпан или срок вышел.
messages-executor-extended = ✅ Заказ №{ $id }: покупатель продлил срок до { $time }
messages-executor-ext_declined = ✖️ Заказ №{ $id }: покупатель не продлил срок, сдать до { $time }

buttons-cancel_yes = ✅ Согласен
buttons-cancel_no = ✖️ Продолжу выполнять
messages-executor-cancel_ask = ↩️ Покупатель просит отменить заказ №{ $id }. Согласны? Если не ответите до { $time }, заказ отменится сам. Штрафа это не несёт.
messages-executor-cancel_wait = ↩️ Покупатель просит отменить заказ. Ответьте до { $time }, иначе заказ отменится сам. Штрафа это не несёт.
messages-executor-cancel_agreed = ↩️ Заказ №{ $id } отменён по договорённости. Штрафа нет.
messages-executor-cancel_by_timer = ↩️ Заказ №{ $id } отменён: вы не ответили на просьбу покупателя за час. Штрафа нет.
messages-executor-cancel_declined = ✖️ Вы продолжаете выполнять заказ №{ $id }.
messages-executor-cancel_stale = Просьба об отмене уже неактуальна.

buttons-info_ask = ❓ Нужны данные
messages-executor-info_prompt =
    ❓ <b>Заказ №{ $id }: нужны данные</b>
    Одним сообщением напишите покупателю, что именно уточнить: до 300 символов, без контактов и ссылок.
    Срок заказа встанет на паузу, пока он не ответит (не дольше суток).
messages-executor-info_invalid = Вопрос должен быть текстом до 300 символов. Напишите короче и отправьте ещё раз.
messages-executor-info_blocked = ⚠️ Вопрос не отправлен: контакты и ссылки запрещены. Задайте вопрос без них.
messages-executor-info_sent = ✅ Вопрос по заказу №{ $id } отправлен покупателю. Срок на паузе, пока он не ответит (не дольше суток).
messages-executor-info_failed = Сейчас нельзя запросить данные по заказу №{ $id }: вопрос уже задан, лимит в 3 вопроса исчерпан, срок вышел или открыт спор.
messages-executor-info_wait = ⏸ Ждём ответа покупателя до { $time }. Срок заказа на паузе.
messages-executor-info_answered = 💬 Покупатель ответил по заказу №{ $id }. Срок продлён до { $time }.
messages-executor-info_timeout = ↩️ Покупатель не ответил на вопрос по заказу №{ $id } за сутки, заказ закрыт, деньги вернулись ему. На вашей статистике это не сказывается.
