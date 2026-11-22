import { useState } from "react";
import { useLocation } from "wouter";
import { report, useBusy } from "../../action";
import { ApiError, send, useFetch, type ExecutorOrder, type ResultField } from "../../api";
import { fmtDate, named, t } from "../../i18n";
import { alert, confirm, failure, success, useMainButton } from "../../telegram";
import { Failure, Field, Loading, Money, Row, Section, list } from "../../ui/kit";
import { ChatRow } from "../../ui/ChatRow";
import { DisputeBlock } from "../../ui/Dispute";
import { Left, duration } from "../../ui/Left";
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

function InfoBlock({ o, id, reload }: { o: ExecutorOrder; id: number; reload: () => void }) {
  const [asking, setAsking] = useState(false);
  const [question, setQuestion] = useState("");
  const { run } = useBusy();
  const send_ = () =>
    run(async () => {
      if (!question.trim()) return;
      try {
        await send("POST", `/executor/orders/${id}/info`, { question });
        success();
        await alert(t("exec.infoSent"));
        setAsking(false);
        setQuestion("");
      } catch (e) {
        if (e instanceof ApiError && e.code === "contacts_blocked") {
          failure();
          return alert(t("chat.contacts"));
        }
        if (e instanceof ApiError && (e.status === 409 || e.status === 400)) await alert(t("exec.infoFailed"));
        else return report(e);
        setAsking(false);
      }
      reload();
    });
  if (o.info)
    return (
      <Section title={t("exec.infoTitle")} footer={t("exec.infoWaiting", { time: fmtDate(o.info.until, true) })}>
        <Row title={o.info.question} />
      </Section>
    );
  if (!o.can_ask_info) return null;
  return (
    <Section title={t("exec.infoTitle")} footer={asking ? t("exec.infoHint") : undefined}>
      {asking ? (
        <>
          <Field label={t("exec.infoQuestion")}>
            <textarea rows={3} autoFocus maxLength={300} value={question} onChange={(e) => setQuestion(e.target.value)} />
          </Field>
          <Row title={t("exec.infoSend")} tone="link" onClick={send_} />
          <Row title={t("cancel")} onClick={() => setAsking(false)} />
        </>
      ) : (
        <Row title={t("exec.infoAsk")} chevron onClick={() => setAsking(true)} />
      )}
    </Section>
  );
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
  const { data: o, error, reload } = useFetch<ExecutorOrder>(`/executor/orders/${id}`, ["order", "message"]);
  const { run } = useBusy();
  const [picking, setPicking] = useState(false);
  if (error && !o) return <Failure error={error} retry={reload} />;
  if (!o) return <Loading />;

  const chat = () =>
    run(async () => {
      try {
        const cid = o.chat?.conversation_id ?? (await send<{ conversation_id: number }>("POST", `/orders/${id}/chat`)).conversation_id;
        go(`/work/order/${id}/chat/${cid}`);
      } catch (e) {
        await report(e);
      }
    });
  const ask = (minutes: number) =>
    run(async () => {
      try {
        await send("POST", `/executor/orders/${id}/extension`, { minutes });
        success();
        setPicking(false);
        reload();
      } catch (e) {
        if (e instanceof ApiError && (e.status === 409 || e.status === 400)) {
          await alert(t("exec.extFailed"));
          setPicking(false);
          reload();
        } else await report(e);
      }
    });
  const accept = () =>
    run(async () => {
      try {
        await send("POST", `/executor/orders/${id}/accept`);
        success();
      } catch (e) {
        if (e instanceof ApiError && e.status === 404) await alert(t("exec.acceptFailed"));
        else return report(e);
      }
      reload();
    });
  const answerCancel = (agree: boolean) =>
    run(async () => {
      const req = o.cancel_request;
      if (!req) return;
      try {
        await send("POST", `/executor/orders/${id}/cancel-request`, { request_id: req.request_id, agree });
        success();
      } catch (e) {
        if (e instanceof ApiError && (e.status === 409 || e.status === 404)) await alert(t("exec.cancelStale"));
        else return report(e);
      }
      reload();
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

  const awaitsHim = o.dispute?.awaiting_role === "executor";
  return (
    <div className="screen">
      <div className="headline">
        <h1>{o.product}</h1>
        <p>{list(o.country?.toUpperCase(), `№${o.id}`)}</p>
      </div>
      {o.accept_until && (
        <Section title={t("exec.acceptTitle")} footer={t("exec.acceptUntil", { time: fmtDate(o.accept_until, true) })}>
          <Row title={t("exec.accept")} tone="link" onClick={accept} />
        </Section>
      )}
      {o.cancel_request && (
        <Section title={t("exec.cancelAsk")} footer={t("exec.cancelAskUntil", { time: fmtDate(o.cancel_request.until, true) })}>
          <Row title={t("exec.cancelYes")} tone="link" onClick={() => answerCancel(true)} />
          <Row title={t("exec.cancelNo")} tone="bad" onClick={() => answerCancel(false)} />
        </Section>
      )}
      {awaitsHim && (
        <DisputeBlock
          path={`/executor/orders/${id}/dispute`}
          can={o.can_dispute}
          dispute={o.dispute}
          me="executor"
          reload={reload}
        />
      )}
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
      {!awaitsHim && (
        <DisputeBlock
          path={`/executor/orders/${id}/dispute`}
          can={o.can_dispute}
          dispute={o.dispute}
          me="executor"
          reload={reload}
        />
      )}
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
      {o.extension && (o.extension.pending_minutes || o.extension.can_request) && (
        <Section title={t("exec.extTitle")} footer={o.extension.pending_minutes ? undefined : t("exec.extHint")}>
          {o.extension.pending_minutes ? (
            <Row title={t("exec.extWaiting", { d: duration(o.extension.pending_minutes) })} />
          ) : picking ? (
            o.extension.options.map((m) => <Row key={m} title={`+${duration(m)}`} chevron onClick={() => ask(m)} />)
          ) : (
            <Row title={t("exec.extAsk")} chevron onClick={() => setPicking(true)} />
          )}
        </Section>
      )}
      <InfoBlock o={o} id={id} reload={reload} />
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
          <ChatRow title={t("exec.writeBuyer")} chat={o.chat} onClick={chat} />
        )}
        {o.status === "assigned" && <Row title={t("exec.refuse")} tone="bad" onClick={refuse} />}
      </Section>
    </div>
  );
}
