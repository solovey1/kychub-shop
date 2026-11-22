import { useLocation } from "wouter";
import { report, useBusy } from "../../action";
import { SwitchRow } from "../../admin/kit";
import { send, useFetch, usePaged, type ExecutorListItem, type QueueItem } from "../../api";
import { fmtDate, named, t } from "../../i18n";
import { useUnread } from "../../unread";
import { Badge, Empty, Failure, Loading, Money, Row, Section, Segments, list, statusTone } from "../../ui/kit";
import { Left } from "../../ui/Left";
import { WalletScreen } from "./Wallet";

export type WorkSeg = "queue" | "mine" | "wallet";

export function Work({ seg }: { seg: WorkSeg }) {
  const [, go] = useLocation();
  const unread = useUnread();
  return (
    <div className="screen">
      <OnlineSwitch />
      <Segments
        value={seg}
        onChange={(s) => go(`/work/${s}`, { replace: true })}
        items={[
          [
            "queue",
            <>
              {t("work.queue")}
              <Badge n={unread.offers} />
            </>,
          ],
          [
            "mine",
            <>
              {t("work.mine")}
              <Badge n={unread.work} />
            </>,
          ],
          ["wallet", t("work.wallet")],
        ]}
      />
      {seg === "queue" ? <Queue /> : seg === "mine" ? <Mine /> : <WalletScreen />}
    </div>
  );
}

function OnlineSwitch() {
  const { data, reload } = useFetch<{ online: boolean }>("/executor/online");
  const { run } = useBusy();
  if (!data) return null;
  return (
    <Section footer={t("work.onlineNote")}>
      <SwitchRow
        label={t("work.online")}
        checked={data.online}
        onChange={(online) =>
          run(async () => {
            try {
              await send("PUT", "/executor/online", { online });
            } catch (e) {
              await report(e);
            }
            reload();
          })
        }
      />
    </Section>
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
  const { items, total, error, more } = usePaged<ExecutorListItem>("/executor/orders", ["order", "message"]);
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
              <span className={statusTone(o.status)}>
                {named("status", o.status)}
              </span>
            }
            rightSub={o.status === "assigned" && o.deadline_at ? <Left until={o.deadline_at} /> : undefined}
            unread={o.unread}
            tag={
              o.action === "work" && o.deadline_at
                ? t("action.work", { time: fmtDate(o.deadline_at, true) })
                : o.action === "dispute"
                  ? t("action.dispute")
                  : undefined
            }
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
