import { useState } from "react";
import { useLocation } from "wouter";
import { report, useBusy } from "../../action";
import { ApiError, send, useFetch, type Order as OrderData } from "../../api";
import { fmtDate, fmtMoney, t } from "../../i18n";
import { alert, confirm, success } from "../../telegram";
import { Failure, Loading, Money, Row, Section, list } from "../../ui/kit";
import { duration } from "../../ui/Left";
import { ChatRow } from "../../ui/ChatRow";
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
  const { data: o, error, reload } = useFetch<OrderData>(`/orders/${id}`, ["order", "message"]);
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
  const askCancel = () =>
    run(async () => {
      if (!(await confirm(t("order.cancelAskConfirm")))) return;
      try {
        await send("POST", `/orders/${id}/cancel-request`);
        success();
        await alert(t("order.cancelAsked"));
      } catch (e) {
        if (e instanceof ApiError && (e.status === 409 || e.status === 404)) await alert(t("order.cancelAskFailed"));
        else return report(e);
      }
      reload();
    });
  const rate = (score: number) =>
    run(async () => {
      try {
        await send("POST", `/orders/${id}/rate`, { score });
        success();
      } catch (e) {
        if (!(e instanceof ApiError && e.status === 400)) return report(e); // rated already
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

  const awaitsHim = o.dispute?.awaiting_role === "buyer";
  const lines = (o.result ?? "").split("\n").filter((l) => l.trim());
  return (
    <div className="screen">
      <div className="headline">
        <h1>{o.product}</h1>
        <p>{list(o.variant, o.country?.toUpperCase(), `№${o.id}`)}</p>
      </div>
      {o.can_confirm && (
        <Section
          title={t("order.confirmHint")}
          footer={o.confirm_at ? t("order.confirmAt", { time: fmtDate(o.confirm_at, true) }) : undefined}
        >
          <Row title={t("order.confirm")} tone="link" onClick={confirmOrder} />
        </Section>
      )}
      {o.info && (
        <Section title={t("order.infoAsk")} footer={t("order.infoUntil", { time: fmtDate(o.info.until, true) })}>
          <Row title={o.info.question} />
          <ChatRow
            title={t("order.infoReply")}
            chat={o.chat}
            onClick={() =>
              chat(
                (cid) => `/orders/${id}/chat/${cid}`,
                async () => (o.chat ? { conversation_id: o.chat.conversation_id } : send("POST", `/orders/${id}/chat`)),
              )
            }
          />
        </Section>
      )}
      {o.can_rate && (
        <Section title={t("order.rate")} footer={t("order.rateHint")}>
          <div className="stars">
            {[1, 2, 3, 4, 5].map((n) => (
              <button key={n} type="button" aria-label={String(n)} onClick={() => rate(n)}>
                ☆
              </button>
            ))}
          </div>
        </Section>
      )}
      {o.rating !== null && (
        <Section>
          <Row title={t("order.rated")} right={"★".repeat(o.rating)} />
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
      {o.cancel_request && (
        <Section>
          <Row title={t("order.cancelWait")} sub={t("order.cancelWaitUntil", { time: fmtDate(o.cancel_request.until, true) })} />
        </Section>
      )}
      {awaitsHim && <DisputeBlock path={`/orders/${id}/dispute`} can={o.can_dispute} dispute={o.dispute} me="buyer" reload={reload} />}
      <Section>
        <Track status={o.status} hasExecutor={!!o.executor_alias} />
      </Section>
      <Section>
        <Row title={t("order.total")} right={<Money value={o.total} />} />
        {o.reserved && <Row title={t("order.reserved")} sub={t("order.reservedNote")} right={<Money value={o.reserved} />} />}
        {o.executor_alias && (
          <Row
            title={t("order.executor")}
            sub={
              o.executor_rating?.score != null
                ? `⭐ ${o.executor_rating.score.toFixed(1)} · ${t("order.ratings", { n: o.executor_rating.count })}`
                : t("order.executorNew")
            }
            right={o.executor_alias}
          />
        )}
        {o.deadline_at && <Row title={t("order.due")} right={fmtDate(o.deadline_at, true)} />}
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
      {!awaitsHim && <DisputeBlock path={`/orders/${id}/dispute`} can={o.can_dispute} dispute={o.dispute} me="buyer" reload={reload} />}
      <Section>
        {(o.status === "assigned" || o.status === "ready") && (
          <ChatRow
            title={t("order.writeExecutor")}
            chat={o.chat}
            onClick={() =>
              chat(
                (cid) => `/orders/${id}/chat/${cid}`,
                async () => (o.chat ? { conversation_id: o.chat.conversation_id } : send("POST", `/orders/${id}/chat`)),
              )
            }
          />
        )}
        {!o.can_dispute && !o.dispute && (
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
        )}
        {o.can_cancel && <Row title={t("order.cancel")} tone="bad" onClick={cancel} />}
        {o.can_ask_cancel && <Row title={t("order.cancelAsk")} sub={t("order.cancelAskHint")} tone="bad" onClick={askCancel} />}
      </Section>
    </div>
  );
}
