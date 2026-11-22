import type { Message, OrderChat } from "../api";
import { known, named, t } from "../i18n";
import { Badge, Row } from "./kit";

function preview(m: Message) {
  const body = m.text ?? (m.media_type ? (known(`media.${m.media_type}`) ? named("media", m.media_type) : t("chat.file", { type: m.media_type })) : "");
  return `${m.mine ? t("chat.you") : named("role", m.sender_role)}: ${body}`;
}

/** «Write to …» row of an order: unread badge and the last message under the title. */
export function ChatRow({ title, chat, onClick }: { title: string; chat: OrderChat | null; onClick: () => void }) {
  const unread = chat?.unread ?? 0;
  return (
    <Row
      title={title}
      sub={chat?.last && <span className={`chat-last${unread > 0 ? " unread" : ""}`}>{preview(chat.last)}</span>}
      right={unread > 0 ? <Badge n={unread} /> : undefined}
      chevron
      onClick={onClick}
    />
  );
}
