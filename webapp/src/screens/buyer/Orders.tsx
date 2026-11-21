import { useState } from "react";
import { useLocation } from "wouter";
import { report, useBusy } from "../../action";
import { send, useFetch, usePaged, type BuyerExecutor, type OrderBrief } from "../../api";
import { named, t } from "../../i18n";
import { Empty, Failure, Loading, Money, Row, Section, Segments, list } from "../../ui/kit";

type Seg = "orders" | "executors";
const ENDED = ["cancelled", "failed", "refunded"];

export function openSupport(orderId: number | null) {
  return send<{ conversation_id: number }>("POST", "/support", { order_id: orderId });
}

export function Orders() {
  const [seg, setSeg] = useState<Seg>("orders");
  return (
    <div className="screen">
      <Segments
        value={seg}
        onChange={setSeg}
        items={[
          ["orders", t("orders.title")],
          ["executors", t("executors.title")],
        ]}
      />
      {seg === "orders" ? <OrderList /> : <MyExecutors />}
    </div>
  );
}

function OrderList() {
  const [, go] = useLocation();
  const { items, total, error, more } = usePaged<OrderBrief>("/orders", ["order"]);
  const { run } = useBusy();
  const support = () =>
    run(async () => {
      try {
        go(`/chat/${(await openSupport(null)).conversation_id}`);
      } catch (e) {
        await report(e);
      }
    });
  return (
    <>
      <Section>
        <Row title={t("support.contact")} chevron onClick={support} tone="link" />
      </Section>
      {error && !items && <Failure error={error} />}
      {!items && !error && <Loading />}
      {items?.length === 0 && <Empty text={t("orders.empty")} />}
      {items && items.length > 0 && (
        <Section title={t("orders.title")}>
          {items.map((o) => (
            <Row
              key={o.id}
              title={o.product}
              sub={list(o.variant, o.country?.toUpperCase())}
              meta={`№${o.id}`}
              right={<Money value={o.total} />}
              rightSub={
                <span className={ENDED.includes(o.status) ? "bad-text" : ""}>
                  {named("status", o.status)}
                </span>
              }
              onClick={() => go(`/orders/${o.id}`)}
            />
          ))}
        </Section>
      )}
      {items && items.length < total && (
        <button className="more" onClick={more}>
          {t("more")}
        </button>
      )}
    </>
  );
}

function MyExecutors() {
  const { data, error, reload } = useFetch<BuyerExecutor[]>("/executors/mine", ["order"]);
  if (error && !data) return <Failure error={error} retry={reload} />;
  if (!data) return <Loading />;
  if (!data.length) return <Empty text={t("executors.empty")} />;
  return (
    <Section footer={t("executors.hint")}>
      {data.map((e) => (
        <Row key={e.alias} title={e.alias} right={t("executors.done", { n: e.completed })} />
      ))}
    </Section>
  );
}
