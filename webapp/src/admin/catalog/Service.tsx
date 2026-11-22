import { useState } from "react";
import { useLocation } from "wouter";
import { ApiError, send, useFetch, type AdminService } from "../../api";
import { named, t } from "../../i18n";
import { confirm } from "../../telegram";
import { Failure, Field, Loading, Row, Section } from "../../ui/kit";
import { SelectField, SwitchRow, useExit, useSave } from "../kit";

const CODE = /^[a-z][a-z0-9_]{1,31}$/;

/** `id` null: a new service. */
export function ServiceForm({ id }: { id: number | null }) {
  const { data, error, reload } = useFetch<AdminService[]>("/admin/services");
  if (error && !data) return <Failure error={error} retry={reload} />;
  if (!data) return <Loading />;
  const service = id === null ? undefined : data.find((s) => s.id === id);
  if (id !== null && !service) return <Failure error={new ApiError(404, null, "")} />;
  return <Editor service={service} />;
}

function Editor({ service }: { service?: AdminService }) {
  const [, go] = useLocation();
  const [code, setCode] = useState("");
  const [title, setTitle] = useState(service?.title ?? "");
  const [deadline, setDeadline] = useState(service ? String(service.deadline_minutes) : "60");
  const [mode, setMode] = useState(service?.assign_mode ?? "queue");
  const [percent, setPercent] = useState(service ? String(service.executor_percent) : "70");
  const [active, setActive] = useState(service?.is_active ?? true);
  const exit = useExit("/admin/catalog/services");

  const valid =
    title.trim() !== "" &&
    (service !== undefined || CODE.test(code)) &&
    Number(deadline) >= 1 &&
    percent !== "" &&
    Number(percent) <= 100;
  const act = useSave(valid ? t("save") : null, async () => {
    const body = {
      title: title.trim(),
      deadline_minutes: Number(deadline),
      assign_mode: mode,
      executor_percent: Number(percent),
      is_active: active,
    };
    if (service) await send("PATCH", `/admin/services/${service.id}`, body);
    else await send("POST", "/admin/services", { ...body, code });
    exit();
  });
  const remove = () =>
    act(async () => {
      if (!service || !(await confirm(t("service.deleteConfirm", { title: service.title })))) return false;
      await send("DELETE", `/admin/services/${service.id}`);
      go("/admin/catalog/services", { replace: true });
    });

  return (
    <div className="screen">
      <div className="headline">
        <h1>{service ? service.title : t("service.new")}</h1>
        {service && <p>{service.code}</p>}
      </div>
      <Section footer={service ? undefined : t("service.codeNote")}>
        {!service && (
          <Field label={t("service.code")} invalid={code !== "" && !CODE.test(code)}>
            <input
              value={code}
              maxLength={32}
              autoCapitalize="none"
              onChange={(e) => setCode(e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, ""))}
            />
          </Field>
        )}
        <Field label={t("service.title")} invalid={!title.trim()}>
          <input value={title} maxLength={100} onChange={(e) => setTitle(e.target.value)} />
        </Field>
        <Field label={t("service.deadline")} invalid={Number(deadline) < 1}>
          <input inputMode="numeric" value={deadline} onChange={(e) => setDeadline(e.target.value.replace(/\D/g, ""))} />
        </Field>
        <SelectField
          label={t("service.mode")}
          value={mode}
          onChange={(v) => setMode(v as AdminService["assign_mode"])}
          options={(["queue", "auto"] as const).map((m) => [m, named("service.mode", m)])}
        />
        <Field label={t("service.percent")} invalid={Number(percent) > 100}>
          <input inputMode="numeric" value={percent} onChange={(e) => setPercent(e.target.value.replace(/\D/g, ""))} />
        </Field>
        <SwitchRow label={t("admin.active")} checked={active} onChange={setActive} />
      </Section>
      {service && (
        <Section footer={t("service.deleteNote")}>
          <Row title={t("service.delete")} tone="bad" onClick={remove} />
        </Section>
      )}
    </div>
  );
}
