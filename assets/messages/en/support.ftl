messages-manager-done = Done.
messages-manager-usage = Usage: /manager_add &lt;tg_id&gt; or /manager_del &lt;tg_id&gt;
messages-manager-err_exists = This user is already a manager.
messages-manager-err_not_found = Manager not found.

messages-chat-ref_ticket = ticket #{ $id }
messages-chat-ref_order = order #{ $id }
messages-chat-from_buyer = <b>Buyer · { $ref }</b>
messages-chat-from_user = <b>{ $name } · { $ref }</b>
messages-chat-from_executor = <b>Executor { $alias } · { $ref }</b>
messages-chat-from_support = <b>Support · { $ref }</b>
messages-chat-hint = To write about an order or to support, open the order or tap "Support" in the menu.
messages-chat-unsupported = This type of message is not supported.
messages-chat-forbidden = You can no longer write here: the conversation is closed or the order was passed to another executor.
messages-chat-order_closed = This order is no longer in work, so its chat is closed. For help, use "Support" in the menu.
messages-chat-saved = Message saved. The reply will arrive in this chat.
messages-chat-undelivered = The message could not be delivered: the recipient is unavailable. It is saved in the history.

buttons-chat_reply = ↩️ Reply
buttons-chat_close = ✖️ Close ticket
buttons-chat_open = 💬 Open chat

buttons-support = 💬 Support
buttons-chat_support = 🆘 Contact support
buttons-chat_executor = 💬 Message the executor
buttons-chat_buyer = Message the buyer

messages-chat-order_missing = Order not found.
messages-chat-support_new = Ticket #{ $id } created. Write your question in one message, photos and files are fine.
messages-chat-support_again = You already have an open ticket #{ $id }. Write here.
messages-chat-no_executor = No executor has been assigned yet.
messages-chat-order_buyer = Everything you write now goes to the executor of order #{ $id }. They will not see your name.
messages-chat-order_executor = Everything you write now goes to the buyer of order #{ $id }.
messages-chat-reply_open = Write: your message goes to this conversation.
messages-chat-media_photo = [photo]
messages-chat-media_document = [file]
messages-chat-media_video = [video]
messages-chat-media_voice = [voice]
messages-chat-media_audio = [audio]
messages-chat-media_animation = [animation]
messages-chat-media_sticker = [sticker]
messages-chat-media_video_note = [video note]

messages-ticket-order = Order: #{ $id }
messages-ticket-new =
    <b>New ticket #{ $id }</b>
    User: { $name }{ $order }

    { $text }
messages-ticket-take_failed = Ticket #{ $id } was already taken by another manager or is closed.
messages-ticket-taken = Ticket #{ $id } is yours.
messages-ticket-taken_by = Ticket #{ $id }: taken by { $name }.
messages-ticket-closed = Ticket #{ $id } closed.
messages-ticket-closed_buyer = Ticket #{ $id } closed. If your question is still open, tap "Support" in the menu.
messages-ticket-unavailable = Ticket #{ $id } is unavailable.
messages-ticket-notice =
    💬 <b>Support, ticket #{ $id }</b>

    { $text }
messages-ticket-joined = 🎧 Support has joined
messages-chat-tip = ✅ Sent. It is easier to reply in the app.
messages-chat-use_app = Reply in the app: a message from the bot will not reach the ticket.
