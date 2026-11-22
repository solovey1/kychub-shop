import { useState } from "react";
import { report, useBusy } from "../action";
import { ApiError, send, type Dispute } from "../api";
import { fmtDate, named, t } from "../i18n";
import { alert, success } from "../telegram";
import { Field, Row, Section } from "./kit";

export type Side = "buyer" | "executor";

/** What a dispute waits for, from the point of view of `me`. */
export function waitLine(d: Dispute, me: Side | "staff"): string {
  if (!d.awaiting_role || !d.awaiting_until) return t("dispute.waitNone");
  const who = d.awaiting_role === me ? t("dispute.from.you") : named("dispute.from", d.awaiting_role);
  return t("dispute.wait", { who, time: fmtDate(d.awaiting_until, true) });
}

/** «Call support» for a side of an order in work, or the banner of the open dispute.
 * `path` is the POST endpoint that opens it. */
export function DisputeBlock({
  path,
  can,
  dispute,
  me,
  reload,
}: {
  path: string;
  can: boolean;
  dispute: Dispute | null;
  me: Side;
  reload: () => void;
}) {
  const [writing, setWriting] = useState(false);
  const [reason, setReason] = useState("");
  const { run } = useBusy();

  if (dispute) {
    return (
      <Section title={t("dispute.open")}>
        <Row title={waitLine(dispute, me)} />
      </Section>
    );
  }
  if (!can) return null;
  const open = () =>
    run(async () => {
      try {
        await send("POST", path, { reason: reason.trim() || null });
        success();
      } catch (e) {
        if (e instanceof ApiError && e.status === 409) await alert(t("dispute.exists"));
        else if (e instanceof ApiError && e.status === 404) await alert(t("dispute.gone"));
        else return report(e);
      }
      setWriting(false);
      reload();
    });
  return (
    <Section footer={writing ? undefined : t("dispute.hint")}>
      {writing ? (
        <>
          <Field label={t("dispute.reason")}>
            <textarea rows={2} autoFocus maxLength={500} value={reason} onChange={(e) => setReason(e.target.value)} />
          </Field>
          <Row title={t("dispute.send")} tone="bad" onClick={open} />
        </>
      ) : (
        <Row title={t("dispute.call")} tone="bad" onClick={() => setWriting(true)} />
      )}
    </Section>
  );
}
