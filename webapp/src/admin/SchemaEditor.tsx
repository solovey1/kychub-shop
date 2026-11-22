import { useState } from "react";
import type { FieldType, FormSchema, I18n, SchemaField } from "../api";
import { named, t } from "../i18n";
import { Field, Row } from "../ui/kit";
import { arrowsAt, compact, fullI18n, I18nFields, SelectField, SwitchRow } from "./kit";

export type Draft = {
  id: number;
  key: string;
  /** the key was typed by hand: stop deriving it from the label */
  keyTouched: boolean;
  type: FieldType;
  required: boolean;
  label: I18n;
  hint: I18n;
  placeholder: I18n;
  /** one per line */
  options: string;
  regex: string;
  maxLength: string;
  maxFiles: string;
  hidden: boolean;
};

const TYPES: FieldType[] = ["text", "email", "number", "choice", "login", "file"];
const KEY_RE = /^[a-z][a-z0-9_]{0,31}$/;
let counter = 0;

const TRANSLIT: Record<string, string> = {
  а: "a", б: "b", в: "v", г: "g", ґ: "g", д: "d", е: "e", ё: "e", є: "ie", ж: "zh", з: "z", и: "i",
  і: "i", ї: "i", й: "y", к: "k", л: "l", м: "m", н: "n", о: "o", п: "p", р: "r", с: "s", т: "t",
  у: "u", ф: "f", х: "kh", ц: "ts", ч: "ch", ш: "sh", щ: "shch", ъ: "", ы: "y", ь: "", э: "e",
  ю: "yu", я: "ya",
};

/** A key from a label: transliterated, [a-z0-9_], starting with a letter. */
export function slug(label: string): string {
  const s = [...label.toLowerCase()]
    .map((c) => TRANSLIT[c] ?? c)
    .join("")
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");
  return s ? (/^[a-z]/.test(s) ? s : `f${s}`).slice(0, 28) : "";
}

function unique(base: string, taken: string[]): string {
  let key = base;
  for (let n = 2; taken.includes(key); n++) key = `${base}_${n}`;
  return key;
}

const newDraft = (taken: string[]): Draft => ({
  id: ++counter,
  key: unique("field", taken),
  keyTouched: false,
  type: "text",
  required: true,
  label: fullI18n(),
  hint: fullI18n(),
  placeholder: fullI18n(),
  options: "",
  regex: "",
  maxLength: "",
  maxFiles: "",
  hidden: false,
});

export const toDrafts = (schema: FormSchema): Draft[] =>
  (schema.fields ?? []).map((f) => ({
    id: ++counter,
    key: f.key,
    keyTouched: true,
    type: f.type,
    required: f.required,
    label: fullI18n(f.label),
    hint: fullI18n(f.hint),
    placeholder: fullI18n(f.placeholder),
    options: (f.options ?? []).join("\n"),
    regex: f.regex ?? "",
    maxLength: f.max_length === undefined ? "" : String(f.max_length),
    maxFiles: f.max_files === undefined ? "" : String(f.max_files),
    hidden: !!f.hidden_from_executor,
  }));

const optional = (v: I18n): I18n | undefined => {
  const c = Object.fromEntries(
    Object.entries(v)
      .map(([k, s]) => [k, s.trim()])
      .filter(([, s]) => s),
  );
  return Object.keys(c).length ? c : undefined;
};
const lines = (s: string) =>
  s
    .split("\n")
    .map((l) => l.trim())
    .filter(Boolean);

/** What the server takes; empty hint, placeholder, regex and options are left out. */
export const toSchema = (drafts: Draft[]): { fields: SchemaField[] } => ({
  fields: drafts.map((d) => ({
    key: d.key,
    type: d.type,
    required: d.required,
    label: compact(d.label),
    hint: optional(d.hint),
    placeholder: optional(d.placeholder),
    options: d.type === "choice" ? lines(d.options) : undefined,
    regex: d.regex.trim() || undefined,
    max_length: d.maxLength.trim() ? Number(d.maxLength) : undefined,
    max_files: d.type === "file" && d.maxFiles.trim() ? Number(d.maxFiles) : undefined,
    hidden_from_executor: d.hidden || undefined,
  })),
});

export const schemaValid = (drafts: Draft[]) =>
  drafts.every(
    (d, i) =>
      KEY_RE.test(d.key) &&
      !drafts.some((o, j) => j < i && o.key === d.key) &&
      d.label.ru.trim() !== "" &&
      (d.type !== "choice" || lines(d.options).length > 0) &&
      (d.maxLength.trim() === "" || (Number(d.maxLength) >= 1 && Number(d.maxLength) <= 4096)) &&
      (d.type !== "file" || d.maxFiles.trim() === "" || (Number(d.maxFiles) >= 1 && Number(d.maxFiles) <= 10)),
  );

export function SchemaEditor({
  title,
  footer,
  value,
  onChange,
  executorCanSee,
  error,
}: {
  title: string;
  footer?: string;
  value: Draft[];
  onChange: (v: Draft[]) => void;
  /** the questionnaire: a field can be hidden from the executor */
  executorCanSee?: boolean;
  /** the verdict of the server on the saved schema */
  error?: string;
}) {
  const [open, setOpen] = useState<number | null>(null);
  const patch = (id: number, p: Partial<Draft>) =>
    onChange(value.map((d) => (d.id === id ? { ...d, ...p } : d)));
  const takenBy = (id: number) => value.filter((d) => d.id !== id).map((d) => d.key);
  const move = (i: number, dir: "up" | "down") => {
    const next = [...value];
    const j = dir === "up" ? i - 1 : i + 1;
    [next[i], next[j]] = [next[j], next[i]];
    onChange(next);
  };
  const add = () => {
    const d = newDraft(value.map((x) => x.key));
    onChange([...value, d]);
    setOpen(d.id);
  };

  return (
    <section className="section">
      <h2>{title}</h2>
      <div className="group">
        {value.map((d, i) => {
          const taken = takenBy(d.id).includes(d.key);
          return (
            <div key={d.id}>
              <Row
                title={d.label.ru.trim() || t("schema.untitled")}
                sub={`${named("schema.type", d.type)} · ${d.key}`}
                right={d.required ? <span className="hint">{t("schema.required")}</span> : undefined}
                chevron
                onClick={() => setOpen(open === d.id ? null : d.id)}
              />
              {open === d.id && (
                <div className="sbody">
                  <I18nFields
                    label={t("schema.label")}
                    value={d.label}
                    invalid={!d.label.ru.trim()}
                    onChange={(label) =>
                      patch(d.id, {
                        label,
                        ...(!d.keyTouched && { key: unique(slug(label.ru) || "field", takenBy(d.id)) }),
                      })
                    }
                  />
                  <Field
                    label={t("schema.key")}
                    invalid={!KEY_RE.test(d.key) || taken}
                    error={taken ? t("schema.keyTaken") : undefined}
                  >
                    <input
                      value={d.key}
                      maxLength={32}
                      autoCapitalize="none"
                      onChange={(e) =>
                        patch(d.id, {
                          key: e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, ""),
                          keyTouched: true,
                        })
                      }
                    />
                  </Field>
                  <SelectField
                    label={t("schema.type")}
                    value={d.type}
                    onChange={(type) => patch(d.id, { type: type as FieldType })}
                    options={TYPES.map((x) => [x, named("schema.type", x)])}
                  />
                  <SwitchRow
                    label={t("schema.requiredField")}
                    checked={d.required}
                    onChange={(required) => patch(d.id, { required })}
                  />
                  {d.type === "choice" && (
                    <Field label={t("schema.options")} invalid={!d.options.trim()}>
                      <textarea
                        rows={4}
                        value={d.options}
                        onChange={(e) => patch(d.id, { options: e.target.value })}
                      />
                    </Field>
                  )}
                  <I18nFields
                    label={t("schema.hint")}
                    value={d.hint}
                    maxLength={200}
                    onChange={(hint) => patch(d.id, { hint })}
                  />
                  <I18nFields
                    label={t("schema.placeholder")}
                    value={d.placeholder}
                    maxLength={64}
                    onChange={(placeholder) => patch(d.id, { placeholder })}
                  />
                  <Field label={t("schema.regex")}>
                    <input
                      value={d.regex}
                      maxLength={256}
                      autoCapitalize="none"
                      onChange={(e) => patch(d.id, { regex: e.target.value })}
                    />
                  </Field>
                  {d.type === "file" && (
                    <Field label={t("schema.maxFiles")}>
                      <input
                        inputMode="numeric"
                        placeholder="1"
                        value={d.maxFiles}
                        onChange={(e) => patch(d.id, { maxFiles: e.target.value.replace(/\D/g, "") })}
                      />
                    </Field>
                  )}
                  <Field label={t("schema.maxLength")}>
                    <input
                      inputMode="numeric"
                      value={d.maxLength}
                      onChange={(e) => patch(d.id, { maxLength: e.target.value.replace(/\D/g, "") })}
                    />
                  </Field>
                  {executorCanSee && (
                    <SwitchRow
                      label={t("schema.hidden")}
                      checked={d.hidden}
                      onChange={(hidden) => patch(d.id, { hidden })}
                    />
                  )}
                  <Row title={t("schema.order")} right={arrowsAt(i, value.length, (dir) => move(i, dir))} />
                  <Row
                    title={t("schema.delete")}
                    tone="bad"
                    onClick={() => (onChange(value.filter((x) => x.id !== d.id)), setOpen(null))}
                  />
                </div>
              )}
            </div>
          );
        })}
        <Row title={t("schema.add")} tone="link" onClick={add} />
      </div>
      {error && <p className="footer bad-text">{error}</p>}
      {footer && <p className="footer">{footer}</p>}
    </section>
  );
}
