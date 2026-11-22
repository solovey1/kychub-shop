import { useState } from "react";
import { useFetch, type AuditRow } from "../../api";
import { fmtDate, named, t } from "../../i18n";
import { Empty, Failure, Field, Loading, Row, Section, list } from "../../ui/kit";
import { SelectField } from "../kit";

const payloadText = (p: Record<string, unknown>) =>
  Object.entries(p)
    .map(([k, v]) => `${k}: ${typeof v === "object" ? JSON.stringify(v) : String(v)}`)
    .join(", ");

export function AuditScreen() {
  const [actor, setActor] = useState("");
  const [action, setAction] = useState("");
  const actions = useFetch<string[]>("/admin/audit/actions");
  const query = [actor && `actor_id=${actor}`, action && `action=${encodeURIComponent(action)}`].filter(Boolean).join("&");
  const { data, error, reload } = useFetch<AuditRow[]>(`/admin/audit${query ? `?${query}` : ""}`);
  return (
    <div className="screen">
      <Section title={t("orders.filters")}>
        <SelectField
          label={t("audit.action")}
          value={action}
          onChange={setAction}
          options={[["", t("audit.allActions")], ...(actions.data ?? []).map((a): [string, string] => [a, named("audit", a)])]}
        />
        <Field label={t("audit.actor")}>
          <input inputMode="numeric" value={actor} onChange={(e) => setActor(e.target.value.replace(/\D/g, ""))} />
        </Field>
      </Section>
      {error && !data && <Failure error={error} retry={reload} />}
      {!data && !error && <Loading />}
      {data?.length === 0 && <Empty text={t("audit.empty")} />}
      {data && data.length > 0 && (
        <Section>
          {data.map((r) => (
            <Row
              key={r.id}
              title={named("audit", r.action)}
              sub={list(r.actor_name ?? (r.actor_id ? `ID ${r.actor_id}` : t("audit.system")), r.target)}
              meta={payloadText(r.payload) || undefined}
              rightSub={fmtDate(r.created_at)}
            />
          ))}
        </Section>
      )}
    </div>
  );
}
