import { useState } from "react";
import { useLocation } from "wouter";
import { useFetch, type StaffOrderBrief, type Ticket } from "../../api";
import { fmtDate, named, t } from "../../i18n";
import { Empty, Failure, Loading, Row, Section, Segments, list } from "../../ui/kit";

export type SupportSeg = "tickets" | "review";
type Scope = "open" | "mine" | "all";

export function Support({ seg, admin }: { seg: SupportSeg; admin: boolean }) {
  const [, go] = useLocation();
  return (
    <div className="screen">
      <Segments
        value={seg}
        onChange={(s) => go(`/support/${s}`, { replace: true })}
        items={[
          ["tickets", t("support.tickets")],
          ["review", t("support.review")],
        ]}
      />
      {seg === "tickets" ? <Tickets admin={admin} /> : <Review />}
    </div>
  );
}

function Tickets({ admin }: { admin: boolean }) {
  const [, go] = useLocation();
  const [scope, setScope] = useState<Scope>("open");
  const { data, error, reload } = useFetch<Ticket[]>(`/tickets?scope=${scope}`, ["ticket"]);
  const scopes: [Scope, string][] = [
    ["open", t("tickets.open")],
    ["mine", t("tickets.mine")],
  ];
  if (admin) scopes.push(["all", t("tickets.all")]);
  return (
    <>
      <Segments small value={scope} items={scopes} onChange={setScope} />
      {error && !data && <Failure error={error} retry={reload} />}
      {!data && !error && <Loading />}
      {data?.length === 0 && <Empty text={t("tickets.empty")} />}
      {data && data.length > 0 && (
        <Section>
          {data.map((tk) => (
            <Row
              key={tk.id}
              title={tk.buyer_name}
              sub={list(`№${tk.id}`, tk.order_id ? t("tickets.order", { id: tk.order_id }) : null)}
              meta={fmtDate(tk.created_at)}
              right={scope === "all" ? named("ticket", tk.status) : undefined}
              chevron
              onClick={() => go(`/ticket/${tk.id}/${tk.conversation_id}`)}
            />
          ))}
        </Section>
      )}
    </>
  );
}

function Review() {
  const [, go] = useLocation();
  const { data, error, reload } = useFetch<StaffOrderBrief[]>("/staff/orders?status=ready", ["order"]);
  if (error && !data) return <Failure error={error} retry={reload} />;
  if (!data) return <Loading />;
  if (!data.length) return <Empty text={t("review.empty")} />;
  return (
    <Section>
      {data.map((o) => (
        <Row
          key={o.id}
          title={o.product}
          sub={list(o.variant, o.country?.toUpperCase())}
          meta={`№${o.id}`}
          rightSub={o.ready_at ? fmtDate(o.ready_at, true) : undefined}
          chevron
          onClick={() => go(`/support/review/${o.id}`)}
        />
      ))}
    </Section>
  );
}
