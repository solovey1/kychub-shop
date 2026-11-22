import { useState } from "react";
import { send, useFetch, type AdminCountry, type AdminService, type ExecutorDetail } from "../../api";
import { t } from "../../i18n";
import { success } from "../../telegram";
import { Failure, Field, Loading, Money, Row, Section, list } from "../../ui/kit";
import { flag, pick, SwitchRow, useExit, useSave } from "../kit";

export function ExecutorScreen({ id }: { id: number }) {
  const executor = useFetch<ExecutorDetail>(`/admin/executors/${id}`);
  const services = useFetch<AdminService[]>("/admin/services");
  const countries = useFetch<AdminCountry[]>("/admin/countries");
  const error = executor.error ?? services.error ?? countries.error;
  if (error && !(executor.data && services.data && countries.data))
    return <Failure error={error} retry={() => (executor.reload(), services.reload(), countries.reload())} />;
  if (!executor.data || !services.data || !countries.data) return <Loading />;
  return <Editor executor={executor.data} services={services.data} countries={countries.data} />;
}

const same = (a: string[], b: string[]) => a.length === b.length && a.every((c) => b.includes(c));

function Editor({
  executor,
  services,
  countries,
}: {
  executor: ExecutorDetail;
  services: AdminService[];
  countries: AdminCountry[];
}) {
  const initial = (sid: number) => executor.permissions.find((p) => p.service_id === sid)?.countries ?? [];
  const [active, setActive] = useState(executor.is_active);
  const [maxParallel, setMaxParallel] = useState(String(executor.max_parallel));
  const [percent, setPercent] = useState(executor.percent_override === null ? "" : String(executor.percent_override));
  const [perms, setPerms] = useState<Record<number, string[]>>(() =>
    Object.fromEntries(services.map((s) => [s.id, initial(s.id)])),
  );
  const [copied, setCopied] = useState(false);
  const exit = useExit("/admin/people/executors");

  const limit = Number(maxParallel);
  const pct = percent === "" ? null : Number(percent);
  const baseChanged =
    active !== executor.is_active || limit !== executor.max_parallel || pct !== executor.percent_override;
  const changed = services.filter((s) => !same(perms[s.id], initial(s.id)));
  const valid = limit >= 1 && limit <= 100 && (pct === null || pct <= 100);

  useSave(valid && (baseChanged || changed.length > 0) ? t("save") : null, async () => {
    if (baseChanged)
      await send("PATCH", `/admin/executors/${executor.id}`, {
        is_active: active,
        max_parallel: limit,
        percent_override: pct,
      });
    for (const s of changed)
      await send("PUT", `/admin/executors/${executor.id}/permissions`, {
        service_id: s.id,
        countries: perms[s.id],
      });
    exit();
  });

  const toggle = (sid: number, code: string, on: boolean) =>
    setPerms({ ...perms, [sid]: on ? [...perms[sid], code] : perms[sid].filter((c) => c !== code) });
  const copy = async () => {
    if (!executor.wallet.wallet) return;
    try {
      await navigator.clipboard.writeText(executor.wallet.wallet);
    } catch {
      return;
    }
    success();
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };
  const { stats } = executor;

  return (
    <div className="screen">
      <div className="headline">
        <h1>{executor.alias}</h1>
        <p>{list(executor.name, `ID ${executor.id}`, executor.online ? t("people.online") : t("people.offline"))}</p>
      </div>
      <Section footer={t("people.percentNote")}>
        <SwitchRow label={t("admin.active")} checked={active} onChange={setActive} />
        <Field label={t("people.maxParallel")} invalid={!(limit >= 1 && limit <= 100)}>
          <input inputMode="numeric" value={maxParallel} onChange={(e) => setMaxParallel(e.target.value.replace(/\D/g, ""))} />
        </Field>
        <Field label={t("people.percent")} invalid={pct !== null && pct > 100}>
          <input inputMode="numeric" value={percent} onChange={(e) => setPercent(e.target.value.replace(/\D/g, ""))} />
        </Field>
      </Section>

      {services.map((s) => (
        <Section key={s.id} title={t("people.permissions", { title: s.title })} footer={countries.length === 0 ? t("catalog.noCountries") : undefined}>
          {countries.map((c) => (
            <SwitchRow
              key={c.code}
              label={`${flag(c.code)} ${pick(c.title)}`}
              checked={perms[s.id].includes(c.code)}
              onChange={(on) => toggle(s.id, c.code, on)}
            />
          ))}
        </Section>
      ))}

      <Section title={t("stats.title")}>
        <Row title={t("stats.completed")} right={stats.completed} />
        <Row title={t("stats.failed")} right={stats.failed} />
        <Row title={t("stats.overdue")} right={stats.overdue} />
        <Row title={t("stats.refused")} right={stats.refused} />
        <Row
          title={t("stats.time")}
          right={stats.avg_minutes === null ? t("none") : t("queue.minutes", { n: Math.round(stats.avg_minutes) })}
        />
        <Row title={t("stats.score")} right={stats.avg_score === null ? t("none") : stats.avg_score.toFixed(1)} />
      </Section>

      <Section title={t("people.wallet")}>
        <Row title={t("wallet.hold")} right={<Money value={executor.wallet.hold} />} />
        <Row title={t("wallet.available")} right={<Money value={executor.wallet.available} />} />
        <Row
          title={executor.wallet.wallet ?? t("none")}
          sub={t("wallet.address")}
          right={executor.wallet.wallet ? <span className="copy">{copied ? t("copied") : t("copy")}</span> : undefined}
          onClick={executor.wallet.wallet ? copy : undefined}
        />
      </Section>
    </div>
  );
}

export function NewExecutor() {
  const [tgId, setTgId] = useState("");
  const [alias, setAlias] = useState("");
  const exit = useExit("/admin/people/executors");
  useSave(tgId !== "" && alias.trim() !== "" ? t("people.addExecutorButton") : null, async () => {
    await send("POST", "/admin/executors", { tg_id: Number(tgId), alias: alias.trim() });
    exit();
  });
  return (
    <div className="screen">
      <div className="headline">
        <h1>{t("people.newExecutor")}</h1>
      </div>
      <Section footer={t("people.newExecutorNote")}>
        <Field label={t("people.tgId")}>
          <input inputMode="numeric" value={tgId} onChange={(e) => setTgId(e.target.value.replace(/\D/g, ""))} />
        </Field>
        <Field label={t("people.alias")}>
          <input value={alias} maxLength={32} onChange={(e) => setAlias(e.target.value)} />
        </Field>
      </Section>
    </div>
  );
}
