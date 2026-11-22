import { useLocation } from "wouter";
import { ApiError, send, useFetch, type StaffMember } from "../../api";
import { useAct } from "../../admin/kit";
import { t } from "../../i18n";
import { alert, confirm } from "../../telegram";
import { Empty, Failure, Loading, Row, Section } from "../../ui/kit";

export function Handover({ tid, me }: { tid: number; me: number }) {
  const [, go] = useLocation();
  const { data, error, reload } = useFetch<StaffMember[]>("/staff/managers");
  const { act } = useAct((e) => {
    if (!(e instanceof ApiError) || e.status !== 404) return false;
    void alert(t("handover.gone")).then(() => go("/support/tickets", { replace: true }));
    return true;
  });
  if (error && !data) return <Failure error={error} retry={reload} />;
  if (!data) return <Loading />;
  const others = data.filter((m) => m.id !== me);
  const hand = (m: StaffMember) =>
    act(async () => {
      if (!(await confirm(t("handover.confirm", { name: m.name })))) return false;
      await send("POST", `/tickets/${tid}/handover`, { manager_id: m.id });
      go("/support/tickets", { replace: true });
    });
  return (
    <div className="screen">
      <div className="headline">
        <h1>{t("handover.title")}</h1>
        <p>{t("ticket.title", { id: tid })}</p>
      </div>
      {others.length === 0 && <Empty text={t("handover.none")} />}
      {others.length > 0 && (
        <Section>
          {others.map((m) => (
            <Row key={m.id} title={m.name} sub={m.admin ? t("role.admin") : undefined} chevron onClick={() => hand(m)} />
          ))}
        </Section>
      )}
    </div>
  );
}
