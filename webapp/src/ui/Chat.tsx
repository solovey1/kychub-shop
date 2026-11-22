import { useCallback, useEffect, useLayoutEffect, useRef, useState, type ReactNode } from "react";
import { report } from "../action";
import { ApiError, blobUrl, get, send, type Message, type Messages } from "../api";
import { fmtDate, named, t } from "../i18n";
import { useLive } from "../live";
import { success } from "../telegram";
import { refreshUnread } from "../unread";
import { Loading } from "./kit";

const LIMIT = 4000;
const COUNT_FROM = 3500;
const PAGE = 30;

function Media({ id, type }: { id: number; type: string }) {
  const kind =
    type === "photo"
      ? "img"
      : ["video", "video_note", "animation"].includes(type)
        ? "video"
        : ["voice", "audio"].includes(type)
          ? "audio"
          : null;
  const [url, setUrl] = useState<string>();
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    if (!kind) return;
    let dead = false;
    let made: string | undefined;
    blobUrl(`/files/${id}`).then(
      (u) => {
        if (dead) URL.revokeObjectURL(u);
        else setUrl((made = u));
      },
      () => setFailed(true),
    );
    return () => {
      dead = true;
      if (made) URL.revokeObjectURL(made);
    };
  }, [id, kind]);
  if (!kind || failed) return <p className="text">{t("chat.file", { type })}</p>;
  if (!url) return <div className="ph" />;
  if (kind === "img") return <img src={url} alt="" />;
  if (kind === "video") return <video src={url} controls playsInline />;
  return <audio src={url} controls />;
}

/** The conversation of an order or a ticket. `version` reloads it (the ticket was taken). */
export function Chat({
  cid,
  title,
  version = 0,
  onClose,
  onHandover,
  header,
}: {
  cid: number;
  title?: string;
  version?: number;
  onClose?: () => void;
  onHandover?: () => void;
  header?: ReactNode;
}) {
  const [items, setItems] = useState<Message[]>();
  const [hasMore, setHasMore] = useState(false);
  const [canPost, setCanPost] = useState(false);
  const [error, setError] = useState<ApiError>();
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const list = useRef<HTMLDivElement>(null);
  const box = useRef<HTMLTextAreaElement>(null);
  const stick = useRef(true);
  const keep = useRef<number | undefined>(undefined);
  const older = useRef(false);
  const marked = useRef(0);

  useEffect(() => {
    stick.current = true;
    get<Messages>(`/conversations/${cid}/messages?limit=${PAGE}`).then(
      (r) => (setItems(r.items), setHasMore(r.has_more), setCanPost(r.can_post), setError(undefined)),
      setError,
    );
  }, [cid, version]);

  useEffect(() => {
    marked.current = 0;
  }, [cid]);
  // the last message of somebody else is on screen: tell the server (his own are read already)
  useEffect(() => {
    const last = items?.[items.length - 1];
    if (!last || last.mine || last.id <= marked.current) return;
    marked.current = last.id;
    send("POST", `/conversations/${cid}/read`, { message_id: last.id }).then(refreshUnread, () => {
      marked.current = 0;
    });
  }, [items, cid]);

  useLayoutEffect(() => {
    const el = list.current;
    if (!el) return;
    if (keep.current !== undefined) el.scrollTop = el.scrollHeight - keep.current;
    else if (stick.current) el.scrollTop = el.scrollHeight;
    keep.current = undefined;
  }, [items]);

  const add = useCallback((m: Message) => {
    const el = list.current;
    stick.current = m.mine || !el || el.scrollHeight - el.scrollTop - el.clientHeight < 80;
    setItems((old) => (old && !old.some((o) => o.id === m.id) ? [...old, m] : old));
  }, []);
  useLive(["message"], (e) => {
    if (e.conversation_id === cid) add(e.message as Message);
  });

  const loadOlder = async () => {
    const first = items?.[0];
    if (!first || !hasMore || older.current) return;
    older.current = true;
    try {
      const r = await get<Messages>(`/conversations/${cid}/messages?limit=${PAGE}&before_id=${first.id}`);
      keep.current = list.current?.scrollHeight ?? 0;
      setItems((old) => [...r.items, ...(old ?? [])]);
      setHasMore(r.has_more);
    } catch {
      // the next scroll to the top tries again
    } finally {
      older.current = false;
    }
  };

  const post = async () => {
    const body = text.trim();
    if (!body || sending) return;
    setSending(true);
    try {
      add(await send<Message>("POST", `/conversations/${cid}/messages`, { text: body }));
      setText("");
      if (box.current) box.current.style.height = "auto";
      success();
    } catch (e) {
      if (e instanceof ApiError && e.status === 409) setCanPost(false);
      else await report(e);
    } finally {
      setSending(false);
    }
  };

  if (error && !items) return <Loading />;
  return (
    <div className="chat">
      {header}
      {title && (
        <div className="chat-bar">
          <span>{title}</span>
          {onHandover && (
            <button className="link" onClick={onHandover}>
              {t("ticket.handover")}
            </button>
          )}
          {onClose && (
            <button className="link" onClick={onClose}>
              {t("ticket.close")}
            </button>
          )}
        </div>
      )}
      <div
        className="messages"
        ref={list}
        onScroll={(e) => e.currentTarget.scrollTop < 60 && void loadOlder()}
      >
        {!items && <Loading />}
        {items?.length === 0 && <p className="empty">{t("chat.empty")}</p>}
        {items?.map((m, i) => {
          const prev = items[i - 1];
          const first = !prev || prev.mine !== m.mine || prev.sender_role !== m.sender_role;
          return (
            <div key={m.id} className={`msg${m.mine ? " mine" : ""}${first && i ? " gap" : ""}`}>
              {!m.mine && first && <span className="who">{named("role", m.sender_role)}</span>}
              {m.media_type && <Media id={m.id} type={m.media_type} />}
              {m.text && <span className="text">{m.text}</span>}
              <time>{fmtDate(m.created_at, true)}</time>
            </div>
          );
        })}
      </div>
      {items &&
        (canPost ? (
          <div className="composer">
            {text.length >= COUNT_FROM && (
              <span className="count">
                {text.length}/{LIMIT}
              </span>
            )}
            <textarea
              ref={box}
              rows={1}
              value={text}
              maxLength={LIMIT}
              placeholder={t("chat.placeholder")}
              onChange={(e) => {
                setText(e.target.value);
                e.target.style.height = "auto";
                e.target.style.height = `${e.target.scrollHeight}px`;
              }}
            />
            <button className="send" disabled={!text.trim() || sending} onClick={post} aria-label={t("chat.send")}>
              <svg viewBox="0 0 24 24">
                <path d="M12 19V5M5 12l7-7 7 7" />
              </svg>
            </button>
          </div>
        ) : (
          <p className="closed">{t("chat.closed")}</p>
        ))}
    </div>
  );
}
