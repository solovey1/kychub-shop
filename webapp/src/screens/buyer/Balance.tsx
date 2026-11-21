import { useLocation } from "wouter";
import { useFetch, type Balance as BalanceData } from "../../api";
import { fmtDate, named, t } from "../../i18n";
import { close } from "../../telegram";
import { Empty, Failure, Loading, Money, Row, Section } from "../../ui/kit";

export function Balance() {
  const [, go] = useLocation();
  const { data, error, reload } = useFetch<BalanceData>("/balance", ["order"]);
  if (error && !data) return <Failure error={error} retry={reload} />;
  if (!data) return <Loading />;
  return (
    <div className="screen">
      <div className="hero">
        <p className="caption">{t("balance.title")}</p>
        <Money value={data.balance} big />
      </div>
      <Section footer={t("balance.hint")}>
        <Row title={t("balance.topup")} tone="link" onClick={close} />
      </Section>
      {data.entries.length === 0 ? (
        <Empty text={t("balance.empty")} />
      ) : (
        <Section title={t("balance.history")}>
          {data.entries.map((e) => (
            <Row
              key={e.id}
              title={named("kind", e.kind)}
              sub={fmtDate(e.created_at)}
              right={<Money value={e.amount} signed />}
              onClick={e.order_id ? () => go(`/orders/${e.order_id}`) : undefined}
            />
          ))}
        </Section>
      )}
    </div>
  );
}
