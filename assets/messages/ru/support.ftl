messages-support =
    💬 <b>Поддержка</b>

    { $order }Опишите вопрос, и менеджер ответит. Обычно в течение часа.
messages-support-open =
    💬 <b>Поддержка</b>

    { $order }У вас открыт тикет №{ $id }.
messages-support-order = 📦 Заказ №{ $id }
messages-support-write = ✍️ Напишите вопрос одним сообщением, можно с фото или файлом.
buttons-support_write = ✍️ Написать в поддержку

messages-manager-done = Готово.
messages-manager-usage = Использование: /manager_add &lt;tg_id&gt; или /manager_del &lt;tg_id&gt;
messages-manager-err_exists = Этот пользователь уже менеджер.
messages-manager-err_not_found = Менеджер не найден.

messages-chat-ref_ticket = тикет № { $id }
messages-chat-ref_order = заказ № { $id }
messages-chat-from_buyer = <b>Покупатель · { $ref }</b>
messages-chat-from_user = <b>{ $name } · { $ref }</b>
messages-chat-from_executor = <b>Исполнитель { $alias } · { $ref }</b>
messages-chat-from_support = <b>Поддержка · { $ref }</b>
messages-chat-hint = Чтобы написать по заказу или в поддержку, откройте заказ или нажмите «Поддержка» в меню.
messages-chat-unsupported = Этот тип сообщений не поддерживается.
messages-chat-forbidden = Сюда писать больше нельзя: переписка закрыта или заказ передан другому исполнителю.
messages-chat-order_closed = Заказ уже не в работе, чат по нему закрыт. Если нужна помощь, нажмите «Поддержка» в меню.
messages-chat-saved = Сообщение сохранено. Ответ придёт в этот чат.
messages-chat-undelivered = Не удалось доставить сообщение: получатель недоступен. Оно сохранено в истории.

buttons-chat_reply = ↩️ Ответить
buttons-chat_close = ✖️ Закрыть тикет
buttons-chat_open = 💬 Открыть чат

buttons-support = 💬 Поддержка
buttons-chat_support = 🆘 Связаться с поддержкой
buttons-chat_executor = 💬 Написать исполнителю
buttons-chat_buyer = Написать покупателю

messages-chat-order_missing = Заказ не найден.
messages-chat-no_executor = Исполнитель ещё не назначен.
messages-chat-order_buyer = Всё, что вы напишете сейчас, получит исполнитель заказа № { $id }. Он не увидит ваше имя.
messages-chat-order_executor = Всё, что вы напишете сейчас, получит покупатель заказа № { $id }.
messages-chat-reply_open = Пишите: сообщение уйдёт в эту переписку.
messages-chat-media_photo = [фото]
messages-chat-media_document = [файл]
messages-chat-media_video = [видео]
messages-chat-media_voice = [голосовое]
messages-chat-media_audio = [аудио]
messages-chat-media_animation = [анимация]
messages-chat-media_sticker = [стикер]
messages-chat-media_video_note = [кружок]

messages-ticket-order = Заказ: № { $id }
messages-ticket-new =
    <b>Новый тикет № { $id }</b>
    Пользователь: { $name }{ $order }

    { $text }
messages-ticket-take_failed = Тикет № { $id } уже взят другим менеджером или закрыт.
messages-ticket-taken = Тикет № { $id } ваш.
messages-ticket-taken_by = Тикет № { $id }: взял { $name }.
messages-ticket-closed = Тикет № { $id } закрыт.
messages-ticket-closed_buyer = Тикет № { $id } закрыт. Если вопрос остался, нажмите «Поддержка» в меню.
messages-ticket-unavailable = Тикет № { $id } недоступен.
messages-ticket-notice =
    💬 <b>Поддержка, тикет № { $id }</b>

    { $text }
messages-ticket-joined = 🎧 Поддержка подключилась
messages-chat-tip = ✅ Отправлено. Ответ придёт сюда, переписка — в приложении.
messages-chat-use_app = Отвечайте в приложении: сообщение из бота в тикет не уйдёт.
