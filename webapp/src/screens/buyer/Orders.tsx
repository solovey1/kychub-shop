import { useLocation } from "wouter";
import { report, useBusy } from "../../action";
import { send, usePaged, type OrderBrief } from "../../api";
import { named, t } from "../../i18n";
import { useUnread } from "../../unread";
import { Empty, Failure, Loading, Money, Row, Section, list } from "../../ui/kit";

const ENDED = ["cancelled", "failed", "refunded"];

export function openSupport(orderId: number | null) {
  return send<{ conversation_id: number }>("POST", "/support", { order_id: orderId });
}

export function Orders() {
  const [, go] = useLocation();
  const { items, total, error, more } = usePaged<OrderBrief>("/orders", ["order", "message"]);
  const unread = useUnread();
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
    <div className="screen">
      <Section>
        <Row title={t("support.contact")} chevron unread={unread.support} onClick={support} tone="link" />
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
              unread={o.unread}
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
    </div>
  );
}
