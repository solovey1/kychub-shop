import { useLocation } from "wouter";
import { useFetch, usePaged, type ExecutorListItem, type QueueItem } from "../../api";
import { named, t } from "../../i18n";
import { Empty, Failure, Loading, Money, Row, Section, Segments, list } from "../../ui/kit";
import { Left } from "../../ui/Left";
import { WalletScreen } from "./Wallet";

export type WorkSeg = "queue" | "mine" | "wallet";
const ENDED = ["cancelled", "failed", "refunded"];

export function Work({ seg }: { seg: WorkSeg }) {
  const [, go] = useLocation();
  return (
    <div className="screen">
      <Segments
        value={seg}
        onChange={(s) => go(`/work/${s}`, { replace: true })}
        items={[
          ["queue", t("work.queue")],
          ["mine", t("work.mine")],
          ["wallet", t("work.wallet")],
        ]}
      />
      {seg === "queue" ? <Queue /> : seg === "mine" ? <Mine /> : <WalletScreen />}
    </div>
  );
}

function Queue() {
  const [, go] = useLocation();
  const { data, error, reload } = useFetch<QueueItem[]>("/executor/queue", ["queue"]);
  if (error && !data) return <Failure error={error} retry={reload} />;
  if (!data) return <Loading />;
  if (!data.length) return <Empty text={t("queue.empty")} />;
  return (
    <Section>
      {data.map((o) => (
        <Row
          key={o.id}
          title={o.product}
          sub={list(o.country?.toUpperCase(), t("queue.minutes", { n: o.deadline_minutes }))}
          meta={`№${o.id}`}
          right={<Money value={o.earning} signed />}
          onClick={() => go(`/work/offer/${o.id}`)}
        />
      ))}
    </Section>
  );
}

function Mine() {
  const [, go] = useLocation();
  const { items, total, error, more } = usePaged<ExecutorListItem>("/executor/orders", ["order"]);
  if (error && !items) return <Failure error={error} />;
  if (!items) return <Loading />;
  if (!items.length) return <Empty text={t("mine.empty")} />;
  return (
    <>
      <Section>
        {items.map((o) => (
          <Row
            key={o.id}
            title={o.product}
            sub={list(o.variant, o.country?.toUpperCase())}
            meta={`№${o.id}`}
            right={
              <span className={ENDED.includes(o.status) ? "bad-text" : ""}>
                {named("status", o.status)}
              </span>
            }
            rightSub={o.status === "assigned" && o.deadline_at ? <Left until={o.deadline_at} /> : undefined}
            onClick={() => go(`/work/order/${o.id}`)}
          />
        ))}
      </Section>
      {items.length < total && (
        <button className="more" onClick={more}>
          {t("more")}
        </button>
      )}
    </>
  );
}
