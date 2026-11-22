import { useEffect, useState } from "react";
import { useLocation } from "wouter";
import { get, send, useFetch, type Broadcast } from "../../api";
import { fmtDate, named, t } from "../../i18n";
import { confirm } from "../../telegram";
import { Empty, Failure, Field, Loading, Row, Section, list } from "../../ui/kit";
import { useExit, useSave } from "../kit";

const oneLine = (text: string) => {
  const line = text.split("\n")[0];
  return line.length > 50 ? `${line.slice(0, 50)}…` : line;
};

const progress = (b: Broadcast) =>
  b.total_count
    ? t("bcast.progress", { sent: b.sent_count, total: b.total_count, failed: b.failed_count })
    : undefined;

export function BroadcastList() {
  const [, go] = useLocation();
  const { data, error, reload } = useFetch<Broadcast[]>("/admin/broadcasts");
  if (error && !data) return <Failure error={error} retry={reload} />;
  if (!data) return <Loading />;
  return (
    <div className="screen">
      {data.length === 0 && <Empty text={t("bcast.empty")} />}
      <Section>
        {data.map((b) => (
          <Row
            key={b.id}
            title={oneLine(b.text)}
            sub={list(named("bcast.status", b.status), progress(b))}
            meta={fmtDate(b.created_at)}
            chevron
            onClick={() => go(`/admin/broadcasts/${b.id}`)}
          />
        ))}
        <Row title={t("bcast.add")} tone="link" onClick={() => go("/admin/broadcasts/new")} />
      </Section>
    </div>
  );
}

/** `id` null: a new draft. */
export function BroadcastForm({ id }: { id: number | null }) {
  const { data, error, reload } = useFetch<Broadcast>(id === null ? null : `/admin/broadcasts/${id}`);
  const sending = data?.status === "sending";
  // the progress of a running send
  useEffect(() => {
    if (!sending) return;
    const timer = setInterval(reload, 3000);
    return () => clearInterval(timer);
  }, [sending, reload]);
  if (error && !data) return <Failure error={error} retry={reload} />;
  if (id !== null && !data) return <Loading />;
  return <Editor broadcast={data} reload={reload} />;
}

function Editor({ broadcast, reload }: { broadcast?: Broadcast; reload: () => void }) {
  const [, go] = useLocation();
  const [text, setText] = useState(broadcast?.text ?? "");
  const exit = useExit("/admin/broadcasts");
  const draft = !broadcast || broadcast.status === "draft";
  const dirty = text !== (broadcast?.text ?? "");

  /** The draft as it is on screen: created or updated, then its id. */
  const store = async () => {
    if (!broadcast) return (await send<{ id: number }>("POST", "/admin/broadcasts", { text })).id;
    if (dirty) await send("PUT", `/admin/broadcasts/${broadcast.id}`, { text });
    return broadcast.id;
  };
  const act = useSave(draft && text.trim() && (dirty || !broadcast) ? t("save") : null, async () => {
    const id = await store();
    if (broadcast) exit();
    else go(`/admin/broadcasts/${id}`, { replace: true });
  });
  const preview = () =>
    act(async () => {
      await send("POST", "/admin/broadcasts/preview", { text });
    });
  const start = () =>
    act(async () => {
      const { count } = await get<{ count: number }>("/admin/broadcasts/recipients");
      if (!(await confirm(t("bcast.startConfirm", { n: count })))) return false;
      const id = await store();
      await send("POST", `/admin/broadcasts/${id}/start`);
      if (broadcast) reload();
      else go(`/admin/broadcasts/${id}`, { replace: true });
    });
  const stop = () =>
    act(async () => {
      if (!broadcast || !(await confirm(t("bcast.stopConfirm")))) return false;
      await send("POST", `/admin/broadcasts/${broadcast.id}/stop`);
      reload();
    });

  const total = broadcast?.total_count ?? 0;
  const done = broadcast ? broadcast.sent_count + broadcast.failed_count : 0;
  return (
    <div className="screen">
      <div className="headline">
        <h1>{broadcast ? t("bcast.title", { id: broadcast.id }) : t("bcast.new")}</h1>
        {broadcast && <p>{named("bcast.status", broadcast.status)}</p>}
      </div>
      <Section footer={draft ? t("bcast.textNote") : undefined}>
        <Field label={t("bcast.text")}>
          <textarea rows={8} maxLength={4096} readOnly={!draft} value={text} onChange={(e) => setText(e.target.value)} />
        </Field>
      </Section>
      {broadcast && broadcast.status !== "draft" && (
        <Section title={t("bcast.progressTitle")}>
          {total > 0 && (
            <div className="bar">
              <i style={{ width: `${Math.min(100, (done / total) * 100)}%` }} />
            </div>
          )}
          <Row title={t("bcast.sent")} right={broadcast.sent_count} />
          <Row title={t("bcast.failed")} right={broadcast.failed_count} />
          {total > 0 && <Row title={t("bcast.total")} right={total} />}
          {broadcast.started_at && <Row title={t("bcast.started")} right={fmtDate(broadcast.started_at)} />}
          {broadcast.finished_at && <Row title={t("bcast.finished")} right={fmtDate(broadcast.finished_at)} />}
        </Section>
      )}
      <Section>
        {draft && text.trim() !== "" && <Row title={t("bcast.preview")} tone="link" onClick={preview} />}
        {draft && text.trim() !== "" && <Row title={t("bcast.start")} tone="link" onClick={start} />}
        {broadcast?.status === "sending" && <Row title={t("bcast.stop")} tone="bad" onClick={stop} />}
      </Section>
    </div>
  );
}
