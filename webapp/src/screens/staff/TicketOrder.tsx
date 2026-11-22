import { useLocation } from "wouter";
import { useFetch, type StaffOrder } from "../../api";
import { named, t } from "../../i18n";
import { Money, Row, list } from "../../ui/kit";
import { Track } from "../../ui/Track";

const flag = (code: string) => String.fromCodePoint(...[...code.toUpperCase()].map((c) => 0x1f1a5 + c.charCodeAt(0)));

/** The order a ticket is about, above the chat, so the manager need not look it up.
 * Open on first view; the buyer's answers include the fields hidden from executors. */
export function TicketOrder({ id }: { id: number }) {
  const [, go] = useLocation();
  const { data: o } = useFetch<StaffOrder>(`/staff/orders/${id}`);
  if (!o) return null; // the chat works without it
  const lines = o.result.split("\n").filter((l) => l.trim());
  return (
    <details className="ticket-order" open>
      <summary>
        {t("ticket.order", { id: o.id })}: {o.product}
      </summary>
      <div className="group">
        <Row title={list(o.variant, o.country && flag(o.country))} right={<Money value={o.total} />} />
        <Track status={o.status} hasExecutor={!!o.executor_alias} />
        <Row title={t("order.status")} right={named("status", o.status)} />
        {o.executor_alias && <Row title={t("order.executor")} right={o.executor_alias} />}
        {o.fields.map((f, i) => (
          <Row key={i} title={f.is_file ? t("exec.fileInBot") : (f.value ?? "")} sub={f.label} />
        ))}
        {lines.length > 0 && <Row title={lines.join("\n")} sub={t("order.result")} />}
        {o.status === "ready" && <Row title={t("ticket.openOrder")} chevron onClick={() => go(`/support/review/${o.id}`)} />}
      </div>
    </details>
  );
}
