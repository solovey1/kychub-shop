import { useState } from "react";
import { useLocation } from "wouter";
import { report, useBusy } from "../../action";
import { ApiError, send, useFetch, type Order as OrderData } from "../../api";
import { fmtDate, fmtMoney, t } from "../../i18n";
import { alert, confirm, success } from "../../telegram";
import { Failure, Loading, Money, Row, Section, list } from "../../ui/kit";
import { duration } from "../../ui/Left";
import { DisputeBlock } from "../../ui/Dispute";
import { Track } from "../../ui/Track";
import { openSupport } from "./Orders";

function ResultLine({ line }: { line: string }) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(line);
    } catch {
      return;
    }
    success();
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };
  return (
    <Row title={line} right={<span className="copy">{copied ? t("copied") : t("copy")}</span>} onClick={copy} />
  );
}

export function OrderScreen({ id }: { id: number }) {
  const [, go] = useLocation();
  const { data: o, error, reload } = useFetch<OrderData>(`/orders/${id}`, ["order"]);
  const { run } = useBusy();
  if (error && !o) return <Failure error={error} retry={reload} />;
  if (!o) return <Loading />;

  const cancel = () =>
    run(async () => {
      if (!(await confirm(t("order.cancelConfirm")))) return;
      try {
        const r = await send<{ refunded: string }>("POST", `/orders/${id}/cancel`);
        success();
        await alert(t("order.cancelled", { sum: fmtMoney(r.refunded) }));
        reload();
      } catch (e) {
        if (e instanceof ApiError && e.status === 404) {
          await alert(t("order.cancelTooLate"));
          reload();
        } else await report(e);
      }
    });
  const confirmOrder = () =>
    run(async () => {
      try {
        await send("POST", `/orders/${id}/confirm`);
        success();
      } catch (e) {
        if (e instanceof ApiError && e.status === 404) await alert(t("order.alreadyDone"));
        else return report(e);
      }
      reload();
    });
  const answer = (approve: boolean) =>
    run(async () => {
      const ext = o.extension;
      if (!ext) return;
      try {
        await send("POST", `/orders/${id}/extension`, { request_id: ext.request_id, approve });
        success();
      } catch (e) {
        if (e instanceof ApiError && (e.status === 409 || e.status === 404)) await alert(t("order.extStale"));
        else return report(e);
      }
      reload();
    });
  const chat = (to: (cid: number) => string, create: () => Promise<{ conversation_id: number }>) =>
    run(async () => {
      try {
        go(to((await create()).conversation_id));
      } catch (e) {
        await report(e);
      }
    });

  const lines = (o.result ?? "").split("\n").filter((l) => l.trim());
  return (
    <div className="screen">
      <div className="headline">
        <h1>{o.product}</h1>
        <p>{list(o.variant, o.country?.toUpperCase(), `№${o.id}`)}</p>
      </div>
      <Section>
        <Track status={o.status} hasExecutor={!!o.executor_alias} />
      </Section>
      <Section>
        <Row title={t("order.total")} right={<Money value={o.total} />} />
        {o.reserved && <Row title={t("order.reserved")} sub={t("order.reservedNote")} right={<Money value={o.reserved} />} />}
        {o.executor_alias && <Row title={t("order.executor")} right={o.executor_alias} />}
        <Row title={t("order.created")} right={fmtDate(o.created_at)} />
      </Section>
      {lines.length > 0 && (
        <Section
          title={t("order.result")}
          footer={o.result_files > 0 ? t("order.files") : undefined}
        >
          {lines.map((l, i) => (
            <ResultLine key={i} line={l} />
          ))}
        </Section>
      )}
      {lines.length === 0 && o.result_files > 0 && (
        <Section title={t("order.result")} footer={t("order.files")}>
          <Row title={t("order.filesCount", { n: o.result_files })} />
        </Section>
      )}
      <DisputeBlock path={`/orders/${id}/dispute`} can={o.can_dispute} dispute={o.dispute} me="buyer" reload={reload} />
      {o.can_confirm && (
        <Section
          title={t("order.confirmHint")}
          footer={o.confirm_at ? t("order.confirmAt", { time: fmtDate(o.confirm_at, true) }) : undefined}
        >
          <Row title={t("order.confirm")} tone="link" onClick={confirmOrder} />
        </Section>
      )}
      {o.extension && (
        <Section
          title={t("order.extAsk", { d: duration(o.extension.minutes) })}
          footer={t("order.extUntil", { time: fmtDate(o.extension.until, true) })}
        >
          <Row title={t("order.extYes")} tone="link" onClick={() => answer(true)} />
          <Row title={t("order.extNo")} tone="bad" onClick={() => answer(false)} />
        </Section>
      )}
      <Section>
        {(o.status === "assigned" || o.status === "ready") && (
          <Row
            title={t("order.writeExecutor")}
            chevron
            onClick={() =>
              chat(
                (cid) => `/orders/${id}/chat/${cid}`,
                () => send("POST", `/orders/${id}/chat`),
              )
            }
          />
        )}
        <Row
          title={t("support.contact")}
          chevron
          onClick={() =>
            chat(
              (cid) => `/chat/${cid}`,
              () => openSupport(id),
            )
          }
        />
        {o.can_cancel && <Row title={t("order.cancel")} tone="bad" onClick={cancel} />}
      </Section>
    </div>
  );
}
