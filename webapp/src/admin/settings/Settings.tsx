import { useState } from "react";
import { send, useFetch, type Tunables } from "../../api";
import { t } from "../../i18n";
import { Failure, Field, Loading, Section } from "../../ui/kit";
import { useSave } from "../kit";

export function SettingsScreen() {
  const { data, error, reload } = useFetch<Tunables>("/admin/settings");
  if (error && !data) return <Failure error={error} retry={reload} />;
  if (!data) return <Loading />;
  return <Editor start={data} />;
}

function Editor({ start }: { start: Tunables }) {
  const [hold, setHold] = useState(String(start.hold_days));
  const [delay, setDelay] = useState(String(start.review_delay_hours));
  const [min, setMin] = useState(start.min_withdrawal);
  const [confirm, setConfirm] = useState(String(start.confirm_hours));
  const [saved, setSaved] = useState(start);

  const body: Tunables = { hold_days: Number(hold), review_delay_hours: Number(delay), min_withdrawal: min.trim(),
    confirm_hours: Number(confirm),
  };
  const valid = hold !== "" && delay !== "" && Number(confirm) >= 1 && Number(confirm) <= 168 && /^\d{1,8}(\.\d{1,2})?$/.test(body.min_withdrawal);
  const changed = JSON.stringify(body) !== JSON.stringify(saved);

  useSave(valid && changed ? t("save") : null, async () => {
    setSaved(await send<Tunables>("PUT", "/admin/settings", body));
  });

  return (
    <div className="screen">
      <div className="headline">
        <h1>{t("admin.settings")}</h1>
      </div>
      <Section>
        <Field label={t("settings.holdDays")} invalid={hold === ""}>
          <input inputMode="numeric" value={hold} onChange={(e) => setHold(e.target.value.replace(/\D/g, ""))} />
        </Field>
        <Field label={t("settings.reviewDelay")} invalid={delay === ""}>
          <input inputMode="numeric" value={delay} onChange={(e) => setDelay(e.target.value.replace(/\D/g, ""))} />
        </Field>
        <Field label={t("settings.confirmHours")} invalid={Number(confirm) < 1 || Number(confirm) > 168}>
          <input inputMode="numeric" value={confirm} onChange={(e) => setConfirm(e.target.value.replace(/\D/g, ""))} />
        </Field>
        <Field label={t("settings.minWithdrawal")} invalid={!valid && min !== ""}>
          <input inputMode="decimal" value={min} onChange={(e) => setMin(e.target.value.replace(",", "."))} />
        </Field>
      </Section>
      <p className="footer">{t("settings.note")}</p>
    </div>
  );
}
