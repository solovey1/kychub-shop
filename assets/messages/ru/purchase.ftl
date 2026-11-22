messages-purchase-head = 🧾 <b>{ $product }</b>, { $details }
messages-purchase-line_done = ✅ { $label }: { $value }
messages-purchase-line_now = ✏️ <b>{ $label }</b>
messages-purchase-line_next = ▫️ { $label }
messages-purchase-line_next_optional = ▫️ { $label } (можно пропустить)
messages-purchase-ask = Введите { $label }
messages-purchase-choose = Выберите { $label }
messages-purchase-hint_file = 📎 Отправьте фото или файл
messages-purchase-files_value =
    📎 { $n ->
        [one] { $n } файл
        [few] { $n } файла
       *[other] { $n } файлов
    }
messages-purchase-hint_files = 📎 Отправьте фото или файлы, до { $max }
messages-purchase-files_progress = 📎 Файлов: { $n } из { $max }
messages-purchase-prompt = ✏️ { $label }
messages-purchase-invalid = ⚠️ { $reason }
messages-purchase-confirm_title = 🧾 <b>Проверьте заказ</b>
messages-purchase-line_price = 💵 Цена: { $amount }
messages-purchase-line_discount = 🎟 Скидка { $code }: −{ $amount }
messages-purchase-line_total = <b>Итого: { $total }</b>, на балансе { $balance }
messages-purchase-line_missing = ⚠️ Не хватает { $amount }
messages-purchase-promo_error = ⚠️ Промокод не применён: { $reason }
messages-purchase-promo_ask = 🎟 Введите промокод одним сообщением.
messages-purchase-edit_pick = ✏️ Что изменить?
messages-purchase-cancelled = ✖️ Оформление отменено.
messages-purchase-accepted =
    ✅ <b>Заказ №{ $id } оплачен</b>

    { $next }
messages-purchase-next_done = Результат придёт следующим сообщением.
messages-purchase-next_queue = Ищем исполнителя.
messages-purchase-next_work = Уже выполняется.
messages-purchase-done = 🎉 <b>Заказ №{ $id } выполнен</b>
messages-purchase-reason_required = ответ обязателен.
messages-purchase-reason_too_long = слишком длинное значение.
messages-purchase-reason_email = это не похоже на адрес почты.
messages-purchase-reason_number = нужно число.
messages-purchase-reason_choice = выберите один из вариантов кнопкой.
messages-purchase-reason_format = значение не соответствует нужному формату.
messages-purchase-reason_control = уберите служебные символы.
messages-purchase-reason_not_file = нужен файл или фото.
messages-purchase-reason_not_text = нужен текст.
messages-purchase-expired = Сессия оформления истекла. Откройте товар заново.
messages-purchase-out_of_stock = Товар закончился. Деньги не списаны.
messages-purchase-unavailable = Товар недоступен. Деньги не списаны.
messages-purchase-done_file = Результат во вложении.
messages-purchase-admin_manual =
    Новый ручной заказ № { $id }
    Покупатель: { $user }
    Товар: { $product }
    { $answers }

messages-promo-reason_not_found = такого кода нет или он отключён.
messages-promo-reason_expired = срок действия истёк.
messages-promo-reason_exhausted = код уже использован максимальное число раз.
messages-promo-reason_not_bonus = это не бонусный код.
messages-promo-reason_bonus_code = это бонусный код, его активируют в разделе «Баланс».
messages-promo-reason_wrong_product = код не подходит для этого товара.
messages-promo-reason_min_amount = сумма заказа меньше минимальной для этого кода.
messages-promo-reason_not_allowed = код вам недоступен.
messages-promo-reason_new_users_only = код только для новых покупателей.
messages-promo-reason_already_used = вы уже использовали этот код.

buttons-pay = ✅ Оплатить { $amount }
buttons-promo = 🎟 Промокод
buttons-skip = ⏭ Пропустить
buttons-copy = 📋 Скопировать
buttons-topup = 💳 Пополнить
buttons-topup_missing = 💳 Пополнить на { $amount }
buttons-edit = ✏️ Изменить ответы
buttons-prev = ↩️ Как в прошлый раз: { $value }
buttons-done = ✅ Готово

messages-purchase-line_online = 🟢 Исполнителей в сети: { $count }
messages-purchase-line_offline = 🌙 Сейчас все не в сети — заказ возьмут, как только кто-то появится
messages-purchase-how_it_works =
    ℹ️ <b>Как это работает</b>
    💰 Деньги ждут в резерве → 🧑‍💻 исполнитель выполняет заказ → ✅ вы проверяете и подтверждаете. Что-то не так — сразу 🆘 в поддержку.
