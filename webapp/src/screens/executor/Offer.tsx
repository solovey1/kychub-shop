import { useLocation } from "wouter";
import { report, useBusy } from "../../action";
import { ApiError, send, useFetch, type QueueItem } from "../../api";
import { t } from "../../i18n";
import { alert, success, useMainButton } from "../../telegram";
import { Empty, Failure, Loading, Money, Row, Section, list } from "../../ui/kit";

export function Offer({ id }: { id: number }) {
  const [, go] = useLocation();
  const { data, error, reload } = useFetch<QueueItem[]>("/executor/queue", ["queue"]);
  const { busy, run } = useBusy();
  const offer = data?.find((o) => o.id === id);

  const take = () =>
    run(async () => {
      try {
        await send("POST", `/executor/orders/${id}/take`);
        success();
        go(`/work/order/${id}`, { replace: true });
      } catch (e) {
        if (e instanceof ApiError && e.status === 409) {
          await alert(t("offer.gone"));
          go("/work/queue", { replace: true });
        } else await report(e);
      }
    });
  useMainButton(offer ? t("offer.take") : null, take, { busy });

  if (error && !data) return <Failure error={error} retry={reload} />;
  if (!data) return <Loading />;
  if (!offer) return <Empty text={t("offer.gone")} />;
  return (
    <div className="screen">
      <div className="headline">
        <h1>{offer.product}</h1>
        <p>{list(offer.country?.toUpperCase(), `№${offer.code}`)}</p>
      </div>
      <Section>
        <Row title={t("offer.earning")} right={<Money value={offer.earning} signed />} />
        <Row title={t("offer.deadline")} right={t("queue.minutes", { n: offer.deadline_minutes })} />
      </Section>
    </div>
  );
}
