import { useState } from "react";
import { useLocation } from "wouter";
import { ApiError, send, useFetch, type Promo, type PromoBrief, type PromoKind } from "../../api";
import { fmtDate, named, t } from "../../i18n";
import { Empty, Failure, Field, Loading, Row, Section, list } from "../../ui/kit";
import { SelectField, SwitchRow, useExit, useSave } from "../kit";

const KINDS: PromoKind[] = ["percent", "amount", "bonus"];
const MONEY = /^\d{1,8}(\.\d{1,2})?$/;
// no look-alikes (0/O, 1/I): a code is often read out or retyped
const CODE_CHARS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";
const randomCode = () => Array.from(crypto.getRandomValues(new Uint8Array(8)), (b) => CODE_CHARS[b % CODE_CHARS.length]).join("");

const value = (p: PromoBrief) => (p.kind === "percent" ? `${p.value}%` : `$${p.value}`);
/** ISO (UTC) to the value of a datetime-local input, in the local zone. */
const toLocal = (iso: string | null) =>
  iso ? new Date(new Date(iso).getTime() - new Date(iso).getTimezoneOffset() * 60_000).toISOString().slice(0, 16) : "";

export function PromoList() {
  const [, go] = useLocation();
  const { data, error, reload } = useFetch<PromoBrief[]>("/admin/promos");
  if (error && !data) return <Failure error={error} retry={reload} />;
  if (!data) return <Loading />;
  return (
    <div className="screen">
      {data.length === 0 && <Empty text={t("promo.empty")} />}
      <Section>
        {data.map((p) => (
          <Row
            key={p.id}
            title={p.code}
            sub={list(
              `${named("promo.kind", p.kind)} ${value(p)}`,
              t("promo.used", { used: p.times_used, limit: p.usage_limit ?? "∞" }),
              p.expires_at ? t("promo.until", { date: fmtDate(p.expires_at) }) : null,
            )}
            dim={!p.active}
            right={p.active ? undefined : <span className="off">{t("admin.off")}</span>}
            chevron
            onClick={() => go(`/admin/promo/${p.id}`)}
          />
        ))}
        <Row title={t("promo.add")} tone="link" onClick={() => go("/admin/promo/new")} />
      </Section>
    </div>
  );
}

/** `id` null: a new promo code. */
export function PromoForm({ id }: { id: number | null }) {
  const { data, error, reload } = useFetch<Promo>(id === null ? null : `/admin/promos/${id}`);
  if (error && !data) return <Failure error={error} retry={reload} />;
  if (id !== null && !data) return <Loading />;
  return <Editor promo={data} />;
}

function Editor({ promo }: { promo?: Promo }) {
  const [, go] = useLocation();
  const [code, setCode] = useState("");
  const [kind, setKind] = useState<PromoKind>(promo?.kind ?? "percent");
  const [amount, setAmount] = useState(promo ? promo.value : "");
  const [limit, setLimit] = useState(promo?.usage_limit?.toString() ?? "");
  const [expires, setExpires] = useState(toLocal(promo?.expires_at ?? null));
  const [productId, setProductId] = useState(promo?.product_id?.toString() ?? "");
  const [minAmount, setMinAmount] = useState(promo?.min_amount ?? "");
  const [newOnly, setNewOnly] = useState(promo?.new_users_only ?? false);
  const [users, setUsers] = useState(promo?.allowed_user_ids.join(", ") ?? "");
  const [reusable, setReusable] = useState(promo?.reusable ?? false);
  const [active, setActive] = useState(promo?.active ?? true);
  const [kindError, setKindError] = useState<string>();
  const exit = useExit("/admin/promo");

  const percent = kind === "percent";
  const ids = users.split(/[\s,]+/).filter(Boolean).map(Number);
  const amountOk = percent ? /^\d+$/.test(amount) && Number(amount) >= 1 && Number(amount) <= 100 : MONEY.test(amount);
  const valid =
    (promo !== undefined || /^[A-Za-z0-9_-]{2,32}$/.test(code)) &&
    amountOk &&
    (minAmount === "" || MONEY.test(minAmount)) &&
    ids.every(Number.isInteger);

  const act = useSave(
    valid ? t("save") : null,
    async () => {
      setKindError(undefined);
      const body = {
        discount_percent: kind === "percent" ? Number(amount) : null,
        discount_amount: kind === "amount" ? amount : null,
        bonus_amount: kind === "bonus" ? amount : null,
        usage_limit: limit === "" ? null : Number(limit),
        expires_at: expires === "" ? null : new Date(expires).toISOString(),
        product_id: productId === "" ? null : Number(productId),
        min_amount: minAmount === "" ? null : minAmount,
        new_users_only: newOnly,
        allowed_user_ids: ids,
        reusable,
        active,
      };
      if (promo) {
        await send("PATCH", `/admin/promos/${promo.id}`, body);
        exit();
      } else {
        const { id } = await send<{ id: number }>("POST", "/admin/promos", { ...body, code: code.trim() });
        go(`/admin/promo/${id}`, { replace: true });
      }
    },
    (e) => {
      if (!(e instanceof ApiError) || e.field !== "kind") return false;
      setKindError(e.detail);
      return true;
    },
  );
  // switching it off is one tap and needs no form
  const toggle = (on: boolean) =>
    act(async () => {
      if (!promo) return false;
      await send("PATCH", `/admin/promos/${promo.id}`, { active: on });
      setActive(on);
    });

  return (
    <div className="screen">
      <div className="headline">
        <h1>{promo ? promo.code : t("promo.new")}</h1>
        {promo && <p>{t("promo.used", { used: promo.times_used, limit: promo.usage_limit ?? "∞" })}</p>}
      </div>
      <Section footer={t("promo.kindNote")}>
        {!promo && (
          <Field label={t("promo.code")}>
            <input value={code} maxLength={32} autoCapitalize="characters" onChange={(e) => setCode(e.target.value.toUpperCase())} />
            <button type="button" className="link" onClick={() => setCode(randomCode())}>
              {t("promo.random")}
            </button>
          </Field>
        )}
        {promo ? (
          <SwitchRow label={t("admin.active")} checked={active} onChange={toggle} />
        ) : (
          <SwitchRow label={t("admin.active")} checked={active} onChange={setActive} />
        )}
        {!promo && (
          <SelectField
            label={t("promo.kind")}
            value={kind}
            onChange={(v) => setKind(v as PromoKind)}
            options={KINDS.map((k) => [k, named("promo.kind", k)])}
          />
        )}
        {promo && <Row title={t("promo.kind")} right={named("promo.kind", kind)} />}
        <Field label={percent ? t("promo.percent") : t("promo.sum")} invalid={amount !== "" && !amountOk} error={kindError}>
          <input inputMode="decimal" value={amount} onChange={(e) => setAmount(e.target.value.replace(",", "."))} />
        </Field>
      </Section>
      <Section title={t("promo.limits")}>
        <Field label={t("promo.limit")}>
          <input inputMode="numeric" value={limit} onChange={(e) => setLimit(e.target.value.replace(/\D/g, ""))} />
        </Field>
        <Field label={t("promo.expires")}>
          <input type="datetime-local" value={expires} onChange={(e) => setExpires(e.target.value)} />
        </Field>
        <Field label={t("promo.product")}>
          <input inputMode="numeric" value={productId} onChange={(e) => setProductId(e.target.value.replace(/\D/g, ""))} />
        </Field>
        <Field label={t("promo.minAmount")} invalid={minAmount !== "" && !MONEY.test(minAmount)}>
          <input inputMode="decimal" value={minAmount} onChange={(e) => setMinAmount(e.target.value.replace(",", "."))} />
        </Field>
        <Field label={t("promo.users")}>
          <input inputMode="numeric" value={users} onChange={(e) => setUsers(e.target.value.replace(/[^\d,\s]/g, ""))} />
        </Field>
        <SwitchRow label={t("promo.newOnly")} checked={newOnly} onChange={setNewOnly} />
        <SwitchRow label={t("promo.reusable")} checked={reusable} onChange={setReusable} />
      </Section>
      {promo && (
        <Section title={t("promo.usages")}>
          {promo.usages.length === 0 && <Row title={t("promo.noUsages")} />}
          {promo.usages.map((u, i) => (
            <Row
              key={i}
              title={u.name}
              sub={list(`ID ${u.user_id}`, u.order_code ? `№${u.order_code}` : null)}
              right={fmtDate(u.created_at)}
            />
          ))}
        </Section>
      )}
    </div>
  );
}
