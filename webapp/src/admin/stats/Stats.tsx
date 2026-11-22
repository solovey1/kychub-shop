import { useState } from "react";
import { useFetch, type StatsData } from "../../api";
import { named, t } from "../../i18n";
import { Failure, Loading, Money, Row, Section, Segments } from "../../ui/kit";

type Days = "1" | "7" | "30";

export function StatsScreen() {
  const [days, setDays] = useState<Days>("7");
  const { data, error, reload } = useFetch<StatsData>(`/admin/stats?days=${days}`);
  return (
    <div className="screen">
      <Segments
        value={days}
        onChange={setDays}
        items={[
          ["1", t("stats.day")],
          ["7", t("stats.week")],
          ["30", t("stats.month")],
        ]}
      />
      {error && !data && <Failure error={error} retry={reload} />}
      {!data && !error && <Loading />}
      {data && <Report data={data} />}
    </div>
  );
}

function Report({ data }: { data: StatsData }) {
  const statuses = Object.entries(data.orders).sort((a, b) => b[1] - a[1]);
  const maxOrders = Math.max(1, ...statuses.map(([, n]) => n));
  const maxRevenue = Math.max(1, ...data.top.map((p) => Number(p.revenue)));
  return (
    <>
      <div className="hero">
        <p className="caption">{t("stats.revenue")}</p>
        <Money value={data.revenue} big />
      </div>
      <Section>
        <Row title={t("stats.refunds")} right={<Money value={data.refunds} />} />
        <Row title={t("stats.topups")} right={<Money value={data.topups} />} />
        <Row title={t("stats.paidOut")} right={<Money value={data.paid_out} />} />
      </Section>
      <Section title={t("stats.liabilities")} footer={t("stats.liabilitiesNote")}>
        <Row title={t("wallet.hold")} right={<Money value={data.hold} />} />
        <Row title={t("wallet.available")} right={<Money value={data.available} />} />
        <Row title={t("stats.buyers")} right={<Money value={data.buyers} />} />
      </Section>
      <Section title={t("stats.orders")}>
        {statuses.length === 0 && <Row title={t("none")} />}
        {statuses.map(([status, n]) => (
          <div className="barrow" key={status}>
            <span>{named("status", status)}</span>
            <b>{n}</b>
            <div className="bar">
              <i style={{ width: `${(n / maxOrders) * 100}%` }} />
            </div>
          </div>
        ))}
      </Section>
      <Section title={t("stats.top")}>
        {data.top.length === 0 && <Row title={t("none")} />}
        {data.top.map((p) => (
          <div className="barrow" key={p.product_id}>
            <span>{p.title}</span>
            <b>
              <Money value={p.revenue} />
            </b>
            <small>{t("stats.ordersCount", { n: p.orders })}</small>
            <div className="bar">
              <i style={{ width: `${(Number(p.revenue) / maxRevenue) * 100}%` }} />
            </div>
          </div>
        ))}
      </Section>
    </>
  );
}
