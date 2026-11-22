import { useState } from "react";
import { useLocation } from "wouter";
import { usePaged, type AdminOrderRow, type Status } from "../../api";
import { named, t } from "../../i18n";
import { Empty, Failure, Field, Loading, Money, Row, Section, list, statusTone } from "../../ui/kit";
import { SelectField } from "../kit";

const STATUSES: Status[] = [
  "awaiting_input",
  "paid",
  "in_queue",
  "assigned",
  "ready",
  "completed",
  "failed",
  "refunded",
  "cancelled",
];

export function AdminOrders() {
  const [, go] = useLocation();
  const [status, setStatus] = useState("");
  const [buyer, setBuyer] = useState("");
  const query = [status && `status=${status}`, buyer && `buyer_id=${buyer}`].filter(Boolean).join("&");
  const { items, total, error, more } = usePaged<AdminOrderRow>(
    `/admin/orders${query ? `?${query}` : ""}`,
    ["order"],
  );
  return (
    <div className="screen">
      <Section title={t("orders.filters")}>
        <SelectField
          label={t("order.status")}
          value={status}
          onChange={setStatus}
          options={[["", t("orders.allStatuses")], ...STATUSES.map((s): [string, string] => [s, named("status", s)])]}
        />
        <Field label={t("orders.buyerId")}>
          <input inputMode="numeric" value={buyer} onChange={(e) => setBuyer(e.target.value.replace(/\D/g, ""))} />
        </Field>
      </Section>
      {error && !items && <Failure error={error} />}
      {!items && !error && <Loading />}
      {items?.length === 0 && <Empty text={t("orders.noneFound")} />}
      {items && items.length > 0 && (
        <Section>
          {items.map((o) => (
            <Row
              key={o.id}
              title={o.product}
              sub={list(o.variant, o.country?.toUpperCase())}
              meta={list(`№${o.id}`, o.executor_alias)}
              right={<Money value={o.total} />}
              rightSub={
                <span className={statusTone(o.status)}>{named("status", o.status)}</span>
              }
              chevron
              onClick={() => go(`/admin/orders/${o.id}`)}
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
