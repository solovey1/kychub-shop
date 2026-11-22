import { useState } from "react";
import { report, useBusy } from "../../action";
import { ApiError, send, useFetch, type Stats, type Wallet } from "../../api";
import { cents, fmtDate, fmtDay, fmtMoney, named, t } from "../../i18n";
import { alert, confirm, success, useMainButton } from "../../telegram";
import { Failure, Field, Loading, Money, Row, Section } from "../../ui/kit";

function Address({ wallet, reload }: { wallet: Wallet; reload: () => void }) {
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState("");
  const [error, setError] = useState<string>();
  const { run } = useBusy();
  const save = () =>
    run(async () => {
      try {
        await send("PUT", "/executor/wallet", { address: value.trim() });
        success();
        setEditing(false);
        setError(undefined);
        reload();
      } catch (e) {
        if (e instanceof ApiError && e.status === 422) setError(e.detail);
        else await report(e);
      }
    });
  if (!editing)
    return (
      <Section title={t("wallet.address")}>
        <Row
          title={wallet.wallet ?? t("wallet.noAddress")}
          tone={wallet.wallet ? undefined : "link"}
          right={wallet.wallet ? t("edit") : undefined}
          onClick={() => (setValue(wallet.wallet ?? ""), setEditing(true))}
        />
      </Section>
    );
  return (
    <Section title={t("wallet.address")}>
      <Field label={t("wallet.addressLabel")} invalid={!!error} error={error}>
        <input autoFocus value={value} maxLength={128} onChange={(e) => setValue(e.target.value)} />
      </Field>
      <Row title={t("save")} tone="link" onClick={save} />
      <Row title={t("cancel")} onClick={() => (setEditing(false), setError(undefined))} />
    </Section>
  );
}

export function WalletScreen() {
  const { data: w, error, reload } = useFetch<Wallet>("/executor/balance", ["order"]);
  const { data: stats } = useFetch<Stats>("/executor/stats", ["order"]);
  const { busy, run } = useBusy();
  const can = !!w && !!w.wallet && cents(w.available) > 0n && cents(w.available) >= cents(w.minimum);

  const withdraw = () =>
    run(async () => {
      if (!w?.wallet) return;
      if (!(await confirm(t("wallet.confirm", { sum: fmtMoney(w.available), address: w.wallet })))) return;
      try {
        await send("POST", "/executor/withdraw");
        success();
        await alert(t("wallet.created"));
        reload();
      } catch (e) {
        await report(e);
      }
    });
  useMainButton(can ? t("wallet.withdraw") : null, withdraw, { busy });

  if (error && !w) return <Failure error={error} retry={reload} />;
  if (!w) return <Loading />;
  const why = !w.wallet
    ? t("wallet.needAddress")
    : cents(w.available) < cents(w.minimum)
      ? t("wallet.minimum", { sum: fmtMoney(w.minimum) })
      : undefined;
  return (
    <>
      <div className="hero">
        <p className="caption">{t("wallet.available")}</p>
        <Money value={w.available} big />
      </div>
      <Section footer={why}>
        {w.hold_days.length === 0 ? (
          <Row title={t("wallet.hold")} right={<Money value={w.hold} />} />
        ) : (
          w.hold_days.map((d) => (
            <Row key={d.date} title={t("wallet.holdOn", { date: fmtDay(d.date) })} right={<Money value={d.amount} />} />
          ))
        )}
        <Row title={t("wallet.min")} right={<Money value={w.minimum} />} />
      </Section>
      <Address wallet={w} reload={reload} />
      {stats && (
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
      )}
      {w.entries.length > 0 && (
        <Section title={t("balance.history")}>
          {w.entries.map((e) => (
            <Row
              key={e.id}
              title={named("kind", e.kind)}
              sub={fmtDate(e.created_at)}
              right={<Money value={e.amount} signed />}
            />
          ))}
        </Section>
      )}
    </>
  );
}
