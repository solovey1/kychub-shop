import { useState } from "react";
import { useLocation } from "wouter";
import { report, useBusy } from "../../action";
import { ApiError, send, useFetch, type StaffOrder } from "../../api";
import { fmtDate, fmtMoney, t } from "../../i18n";
import { alert, confirm, success, useMainButton } from "../../telegram";
import { Failure, Field, Loading, Money, Row, Section, list } from "../../ui/kit";

export function ReviewOrder({ id }: { id: number }) {
  const [, go] = useLocation();
  const { data: o, error, reload } = useFetch<StaffOrder>(`/staff/orders/${id}`);
  const [writing, setWriting] = useState(false);
  const [comment, setComment] = useState("");
  const { busy, run } = useBusy();

  const done = () => {
    success();
    go("/support/review", { replace: true });
  };
  // a second decision on an order already decided looks like a missing one
  const act = (fn: () => Promise<unknown>) =>
    run(async () => {
      try {
        await fn();
        done();
      } catch (e) {
        if (e instanceof ApiError && e.status === 404) {
          await alert(t("review.decided"));
          go("/support/review", { replace: true });
        } else await report(e);
      }
    });

  const confirmOrder = () => act(() => send("POST", `/staff/orders/${id}/confirm`));
  const sendBack = () =>
    comment.trim() ? act(() => send("POST", `/staff/orders/${id}/send_back`, { comment: comment.trim() })) : undefined;
  const fail = async () => {
    if (!o || !(await confirm(t("review.failConfirm", { sum: fmtMoney(o.total) })))) return;
    await act(() => send("POST", `/staff/orders/${id}/fail`));
  };
  useMainButton(o ? t("review.confirm") : null, confirmOrder, { busy });

  if (error && !o) return <Failure error={error} retry={reload} />;
  if (!o) return <Loading />;
  const lines = o.result.split("\n").filter((l) => l.trim());
  return (
    <div className="screen">
      <div className="headline">
        <h1>{o.product}</h1>
        <p>{list(o.variant, o.country?.toUpperCase(), `№${o.id}`)}</p>
      </div>
      <Section>
        <Row title={t("order.total")} right={<Money value={o.total} />} />
        <Row title={t("offer.earning")} right={<Money value={o.earning} />} />
        {o.ready_at && <Row title={t("review.ready")} right={fmtDate(o.ready_at)} />}
      </Section>
      {o.fields.length > 0 && (
        <Section title={t("exec.fields")}>
          {o.fields.map((f, i) => (
            <Row key={i} title={f.is_file ? t("exec.fileInBot") : (f.value ?? "")} sub={f.label} />
          ))}
        </Section>
      )}
      <Section title={t("order.result")} footer={o.result_files > 0 ? t("review.files") : undefined}>
        {lines.length === 0 && <Row title={t("none")} />}
        {lines.map((l, i) => (
          <Row key={i} title={l} />
        ))}
      </Section>
      {writing && (
        <Section>
          <Field label={t("review.comment")}>
            <textarea rows={3} autoFocus maxLength={1000} value={comment} onChange={(e) => setComment(e.target.value)} />
          </Field>
          <Row title={t("review.sendComment")} tone="link" onClick={sendBack} />
        </Section>
      )}
      <Section>
        {!writing && <Row title={t("review.sendBack")} chevron onClick={() => setWriting(true)} />}
        <Row title={t("review.fail")} tone="bad" onClick={fail} />
      </Section>
    </div>
  );
}
