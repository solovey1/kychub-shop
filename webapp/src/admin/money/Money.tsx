import { useState } from "react";
import { send, useFetch, type Withdrawal } from "../../api";
import { fmtDate, t } from "../../i18n";
import { alert, success } from "../../telegram";
import { Empty, Failure, Field, Loading, Money, Row, Section, Segments, list } from "../../ui/kit";
import { useAct } from "../kit";

type Status = Withdrawal["status"];
type Mode = { id: number; kind: "pay" | "reject" };

export function MoneyScreen() {
  const [status, setStatus] = useState<Status>("pending");
  return (
    <div className="screen">
      <Segments
        value={status}
        onChange={setStatus}
        items={[
          ["pending", t("money.pending")],
          ["paid", t("money.paid")],
          ["rejected", t("money.rejected")],
        ]}
      />
      <Withdrawals status={status} />
    </div>
  );
}

function Withdrawals({ status }: { status: Status }) {
  const { data, error, reload } = useFetch<Withdrawal[]>(`/admin/withdrawals?status=${status}`);
  const [mode, setMode] = useState<Mode>();
  const [text, setText] = useState("");
  const [copied, setCopied] = useState<number>();
  const { act } = useAct();

  const decide = (w: Withdrawal, kind: Mode["kind"]) =>
    act(async () => {
      const body = kind === "pay" ? { tx_hash: text.trim() } : { reason: text.trim() };
      const r = await send<{ changed: boolean }>("POST", `/admin/withdrawals/${w.id}/${kind}`, body);
      setMode(undefined);
      setText("");
      if (!r.changed) await alert(t("money.decided"));
      reload();
    });
  const copy = async (w: Withdrawal) => {
    try {
      await navigator.clipboard.writeText(w.address);
    } catch {
      return;
    }
    success();
    setCopied(w.id);
    setTimeout(() => setCopied(undefined), 1500);
  };

  if (error && !data) return <Failure error={error} retry={reload} />;
  if (!data) return <Loading />;
  if (data.length === 0) return <Empty text={t("money.empty")} />;
  return (
    <>
      {data.map((w) => (
        <Section key={w.id} title={list(w.alias ?? w.name, `№${w.id}`)}>
          <Row title={t("money.amount")} right={<Money value={w.amount} />} />
          <Row
            title={w.address}
            sub={t("wallet.address")}
            right={<span className="copy">{copied === w.id ? t("copied") : t("copy")}</span>}
            onClick={() => copy(w)}
          />
          <Row title={t("money.created")} right={fmtDate(w.created_at)} />
          {w.tx_hash && <Row title={w.tx_hash} sub={t("money.txHash")} />}
          {w.reject_reason && <Row title={w.reject_reason} sub={t("money.reason")} />}
          {status === "pending" && mode?.id !== w.id && (
            <>
              <Row title={t("money.pay")} tone="link" onClick={() => (setMode({ id: w.id, kind: "pay" }), setText(""))} />
              <Row title={t("money.reject")} tone="bad" onClick={() => (setMode({ id: w.id, kind: "reject" }), setText(""))} />
            </>
          )}
          {mode?.id === w.id && (
            <>
              <Field label={mode.kind === "pay" ? t("money.txHash") : t("money.reason")}>
                <input
                  autoFocus
                  value={text}
                  maxLength={mode.kind === "pay" ? 128 : 500}
                  autoCapitalize="none"
                  onChange={(e) => setText(e.target.value)}
                />
              </Field>
              {(mode.kind === "pay" ? text.trim().length >= 4 : text.trim() !== "") && (
                <Row
                  title={mode.kind === "pay" ? t("money.confirmPay") : t("money.confirmReject")}
                  tone={mode.kind === "pay" ? "link" : "bad"}
                  onClick={() => decide(w, mode.kind)}
                />
              )}
              <Row title={t("cancel")} onClick={() => setMode(undefined)} />
            </>
          )}
        </Section>
      ))}
    </>
  );
}
