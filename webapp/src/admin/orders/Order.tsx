import { useState } from "react";
import { useLocation } from "wouter";
import { alert as tgAlert, confirm } from "../../telegram";
import { ApiError, send, useFetch, type AdminOrder, type Assignable } from "../../api";
import { fmtDate, fmtMoney, named, t } from "../../i18n";
import { Failure, Field, Loading, Money, Row, Section, list } from "../../ui/kit";
import { allowed } from "../access";
import { useAct, useExit } from "../kit";

const payloadText = (p: Record<string, unknown>) =>
  Object.entries(p)
    .map(([k, v]) => `${k}: ${typeof v === "object" ? JSON.stringify(v) : String(v)}`)
    .join(", ");

export function AdminOrderScreen({ id, viewer }: { id: number; viewer: string[] }) {
  const { data: o, error, reload } = useFetch<AdminOrder>(`/admin/orders/${id}`, ["order"]);
  const [, go] = useLocation();
  const [writing, setWriting] = useState(false);
  const [comment, setComment] = useState("");
  // a second decision on an order already decided looks like a missing one
  const { act } = useAct((e) => {
    if (!(e instanceof ApiError) || e.status !== 404) return false;
    void tgAlert(t("review.decided")).then(reload);
    return true;
  });

  if (error && !o) return <Failure error={error} retry={reload} />;
  if (!o) return <Loading />;

  const run = (fn: () => Promise<unknown>) =>
    act(async () => {
      await fn();
      setWriting(false);
      setComment("");
      reload();
    });
  const refund = (reason: "fail" | "cancel") =>
    act(async () => {
      if (!(await confirm(t(reason === "fail" ? "aorder.failConfirm" : "aorder.cancelConfirm", { sum: fmtMoney(o.total) }))))
        return false;
      await send("POST", `/admin/orders/${id}/refund`, { reason });
      reload();
    });
  const dates: [string, string | null][] = [
    [t("order.created"), o.created_at],
    [t("aorder.assigned"), o.assigned_at],
    [t("aorder.deadline"), o.deadline_at],
    [t("review.ready"), o.ready_at],
    [t("aorder.completed"), o.completed_at],
  ];
  const lines = o.result.split("\n").filter((l) => l.trim());
  const has = (a: string) => o.actions.includes(a);

  return (
    <div className="screen">
      <div className="headline">
        <h1>{o.product}</h1>
        <p>{list(o.variant, o.country?.toUpperCase(), `№${o.code}`)}</p>
      </div>
      <Section>
        <Row title={t("order.status")} right={named("status", o.status)} />
        <Row title={t("aorder.price")} right={<Money value={o.price} />} />
        {o.discount !== "0.00" && <Row title={t("aorder.discount")} right={<Money value={o.discount} />} />}
        <Row title={t("order.total")} right={<Money value={o.total} />} />
        <Row
          title={t("aorder.buyer")}
          sub={`ID ${o.buyer_id}`}
          right={o.buyer_name}
          chevron={allowed(viewer, "users")}
          onClick={allowed(viewer, "users") ? () => go(`/admin/people/u/${o.buyer_id}`) : undefined}
        />
        <Row title={t("order.executor")} right={o.executor_alias ?? t("none")} />
        {dates.map(([label, at]) => at && <Row key={label} title={label} right={fmtDate(at)} />)}
      </Section>

      {o.fields.length > 0 && (
        <Section title={t("exec.fields")}>
          {o.fields.map((f, i) => (
            <Row key={i} title={f.is_file ? t("exec.fileInBot") : (f.value ?? "")} sub={f.label} />
          ))}
        </Section>
      )}
      {(lines.length > 0 || o.result_files > 0) && (
        <Section title={t("order.result")} footer={o.result_files > 0 ? t("order.filesCount", { n: o.result_files }) : undefined}>
          {lines.map((l, i) => (
            <Row key={i} title={l} />
          ))}
        </Section>
      )}

      {o.actions.length > 0 && (
        <Section title={t("aorder.actions")}>
          {has("assign") && <Row title={t("aorder.assign")} chevron onClick={() => go(`/admin/orders/${id}/assign`)} />}
          {has("confirm") && (
            <Row title={t("review.confirm")} tone="link" onClick={() => run(() => send("POST", `/staff/orders/${id}/confirm`))} />
          )}
          {has("send_back") && !writing && <Row title={t("review.sendBack")} chevron onClick={() => setWriting(true)} />}
          {has("send_back") && writing && (
            <>
              <Field label={t("review.comment")}>
                <textarea rows={3} autoFocus maxLength={1000} value={comment} onChange={(e) => setComment(e.target.value)} />
              </Field>
              {comment.trim() && (
                <Row
                  title={t("review.sendComment")}
                  tone="link"
                  onClick={() => run(() => send("POST", `/staff/orders/${id}/send_back`, { comment: comment.trim() }))}
                />
              )}
            </>
          )}
          {has("refund") && <Row title={t("review.fail")} tone="bad" onClick={() => refund("fail")} />}
          {has("cancel") && <Row title={t("aorder.cancel")} tone="bad" onClick={() => refund("cancel")} />}
        </Section>
      )}

      <Section title={t("aorder.events")}>
        {o.events.length === 0 && <Row title={t("none")} />}
        {o.events.map((e) => (
          <Row
            key={e.id}
            title={named("event", e.type)}
            sub={payloadText(e.payload) || undefined}
            right={fmtDate(e.created_at)}
          />
        ))}
      </Section>
      <Section title={t("aorder.ledger")}>
        {o.entries.length === 0 && <Row title={t("none")} />}
        {o.entries.map((e) => (
          <Row
            key={e.id}
            title={named("kind", e.kind)}
            sub={list(named("account", e.account), `ID ${e.user_id}`)}
            right={<Money value={e.amount} signed />}
          />
        ))}
      </Section>
    </div>
  );
}

export function AssignScreen({ id }: { id: number }) {
  const order = useFetch<AdminOrder>(`/admin/orders/${id}`);
  const execs = useFetch<Assignable[]>(`/admin/orders/${id}/executors`);
  const exit = useExit(`/admin/orders/${id}`);
  const { act } = useAct((e) => {
    if (!(e instanceof ApiError) || e.status !== 409 || e.code !== "changed") return false;
    void tgAlert(t("conflict.changed")).then(() => (order.reload(), execs.reload()));
    return true;
  });
  const error = order.error ?? execs.error;
  if (error && !(order.data && execs.data))
    return <Failure error={error} retry={() => (order.reload(), execs.reload())} />;
  if (!order.data || !execs.data) return <Loading />;
  const expected = order.data.executor_id;
  const code = order.data.code;

  const assign = (e: Assignable) =>
    act(async () => {
      if (!(await confirm(t("assign.confirm", { alias: e.alias, id: code })))) return false;
      await send("POST", `/admin/orders/${id}/assign`, { executor_id: e.id, expected_executor_id: expected });
      exit();
    });
  return (
    <div className="screen">
      <div className="headline">
        <h1>{t("assign.title")}</h1>
        <p>{`${order.data.product} · №${order.data.code}`}</p>
      </div>
      <Section footer={t("assign.note")}>
        {execs.data.length === 0 && <Row title={t("assign.none")} />}
        {execs.data.map((e) => (
          <Row
            key={e.id}
            title={e.alias}
            sub={t("assign.load", { n: e.load, max: e.max_parallel })}
            dim={!e.online}
            right={
              e.current ? (
                <span className="hint">{t("assign.current")}</span>
              ) : e.online ? undefined : (
                <span className="off">{t("people.offline")}</span>
              )
            }
            chevron={!e.current}
            onClick={e.current ? undefined : () => assign(e)}
          />
        ))}
      </Section>
    </div>
  );
}
