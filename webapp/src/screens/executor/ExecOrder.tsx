import { useState } from "react";
import { useLocation } from "wouter";
import { report, useBusy } from "../../action";
import { ApiError, send, useFetch, type ExecutorOrder, type ResultField } from "../../api";
import { named, t } from "../../i18n";
import { confirm, failure, success, useMainButton } from "../../telegram";
import { Failure, Field, Loading, Money, Row, Section, list } from "../../ui/kit";
import { Left } from "../../ui/Left";
import { Track } from "../../ui/Track";

function Input({
  f,
  value,
  onChange,
}: {
  f: ResultField;
  value: string;
  onChange: (v: string) => void;
}) {
  const common = { value, maxLength: f.max_length, onChange: (e: { target: { value: string } }) => onChange(e.target.value) };
  if (f.type === "textarea") return <textarea rows={3} {...common} />;
  if (f.type === "select")
    return (
      <select {...common}>
        <option value="" />
        {f.options?.map((o) => (
          <option key={o}>{o}</option>
        ))}
      </select>
    );
  const kind = f.type === "email" ? "email" : f.type === "number" ? "number" : "text";
  return <input type={kind} inputMode={kind === "number" ? "decimal" : undefined} {...common} />;
}

function ResultForm({ id, form, reload }: { id: number; form: ResultField[]; reload: () => void }) {
  const [values, setValues] = useState<Record<string, string>>({});
  const [bad, setBad] = useState<string[]>([]);
  const [message, setMessage] = useState<string>();
  const { busy, run } = useBusy();
  const fileBlocks = form.some((f) => f.type === "file" && f.required);

  const submit = () =>
    run(async () => {
      const missing = form.filter((f) => f.type !== "file" && f.required && !values[f.key]?.trim());
      if (missing.length) {
        setBad(missing.map((f) => f.key));
        setMessage(t("form.required"));
        failure();
        return;
      }
      const fields = Object.fromEntries(
        form.filter((f) => f.type !== "file" && values[f.key]?.trim()).map((f) => [f.key, values[f.key]]),
      );
      try {
        await send("POST", `/executor/orders/${id}/result`, { fields });
        success();
        reload();
      } catch (e) {
        if (e instanceof ApiError && e.status === 422) {
          failure();
          setBad(form.filter((f) => e.detail.includes(f.key) || e.detail.includes(f.label)).map((f) => f.key));
          setMessage(e.detail);
        } else await report(e);
      }
    });
  useMainButton(fileBlocks ? null : t("form.submit"), submit, { busy });

  return (
    <Section title={t("form.title")} footer={message ?? (fileBlocks ? t("form.fileBlocks") : undefined)}>
      {form.map((f) =>
        f.type === "file" ? (
          <Row key={f.key} title={f.label} sub={t("form.fileInBot")} />
        ) : (
          <Field key={f.key} label={f.required ? f.label : `${f.label}, ${t("form.optional")}`} invalid={bad.includes(f.key)}>
            <Input
              f={f}
              value={values[f.key] ?? ""}
              onChange={(v) => {
                setValues({ ...values, [f.key]: v });
                setBad(bad.filter((k) => k !== f.key));
              }}
            />
          </Field>
        ),
      )}
    </Section>
  );
}

export function ExecOrder({ id }: { id: number }) {
  const [, go] = useLocation();
  const { data: o, error, reload } = useFetch<ExecutorOrder>(`/executor/orders/${id}`, ["order"]);
  const { run } = useBusy();
  if (error && !o) return <Failure error={error} retry={reload} />;
  if (!o) return <Loading />;

  const chat = () =>
    run(async () => {
      try {
        const r = await send<{ conversation_id: number }>("POST", `/orders/${id}/chat`);
        go(`/work/order/${id}/chat/${r.conversation_id}`);
      } catch (e) {
        await report(e);
      }
    });
  const refuse = () =>
    run(async () => {
      if (!(await confirm(t("exec.refuseConfirm")))) return;
      try {
        await send("POST", `/executor/orders/${id}/refuse`);
        success();
        go("/work/mine", { replace: true });
      } catch (e) {
        await report(e);
      }
    });

  return (
    <div className="screen">
      <div className="headline">
        <h1>{o.product}</h1>
        <p>{list(o.country?.toUpperCase(), `№${o.id}`)}</p>
      </div>
      <Section>
        <Track status={o.status} hasExecutor />
      </Section>
      <Section>
        <Row title={t("offer.earning")} right={<Money value={o.earning} signed />} />
        <Row title={t("exec.status")} right={named("status", o.status)} />
        {o.status === "assigned" && o.deadline_at && (
          <Row title={t("exec.left")} right={<Left until={o.deadline_at} />} />
        )}
      </Section>
      {o.fields.length > 0 && (
        <Section title={t("exec.fields")}>
          {o.fields.map((f, i) => (
            <Row
              key={i}
              title={f.is_file ? t("exec.fileInBot") : (f.value ?? "")}
              sub={f.label}
            />
          ))}
        </Section>
      )}
      {o.result_form && <ResultForm id={id} form={o.result_form} reload={reload} />}
      {o.result && !o.result_form && (
        <Section title={t("exec.result")}>
          {Object.entries(o.result).map(([k, v]) => (
            <Row key={k} title={v} sub={k} />
          ))}
        </Section>
      )}
      <Section>
        {(o.status === "assigned" || o.status === "ready") && (
          <Row title={t("exec.writeBuyer")} chevron onClick={chat} />
        )}
        {o.status === "assigned" && <Row title={t("exec.refuse")} tone="bad" onClick={refuse} />}
      </Section>
    </div>
  );
}
