import type { ReactNode } from "react";
import { useLocation } from "wouter";
import { report, useBusy } from "../action";
import type { I18n } from "../api";
import { getLang, t } from "../i18n";
import { canGoBack } from "../nav";
import { success, useMainButton } from "../telegram";
import { Field } from "../ui/kit";

export const LANGS = ["ru", "en", "uk"] as const;

/** All three languages present, so every input is controlled. */
export const fullI18n = (v?: I18n | null): I18n => ({ ru: v?.ru ?? "", en: v?.en ?? "", uk: v?.uk ?? "" });

/** Trimmed, without empty translations (`ru` stays unless `ruOptional`: the server requires it). */
export const compact = (v: I18n, ruOptional = false): I18n =>
  Object.fromEntries(
    Object.entries(v)
      .map(([k, s]) => [k, s.trim()])
      .filter(([k, s]) => s || (k === "ru" && !ruOptional)),
  );

/** A text in the current language, falling back to ru. */
export const pick = (v: I18n | null | undefined) => v?.[getLang()] || v?.ru || "";

/** ISO-3166 alpha-2 as a flag emoji. */
export const flag = (code: string) =>
  [...code.toUpperCase()].map((c) => String.fromCodePoint(0x1f1a5 + c.charCodeAt(0))).join("");

export function I18nFields({
  label,
  value,
  onChange,
  rows,
  maxLength,
  invalid,
  error,
}: {
  label: string;
  value: I18n;
  onChange: (v: I18n) => void;
  /** a textarea of this height instead of a single line */
  rows?: number;
  maxLength?: number;
  invalid?: boolean;
  error?: string;
}) {
  return (
    <Field label={label} invalid={invalid} error={error}>
      <div className="langs">
        {LANGS.map((l) => {
          const props = {
            value: value[l] ?? "",
            maxLength,
            onChange: (e: { target: { value: string } }) => onChange({ ...value, [l]: e.target.value }),
          };
          return (
            <div className="lang" key={l}>
              <b>{l.toUpperCase()}</b>
              {rows ? <textarea rows={rows} {...props} /> : <input {...props} />}
            </div>
          );
        })}
      </div>
    </Field>
  );
}

export function SwitchRow({
  label,
  checked,
  onChange,
}: {
  label: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <label className="row">
      <span className="row-main">
        <span className="row-title">{label}</span>
      </span>
      <input
        type="checkbox"
        role="switch"
        className="switch"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
      />
    </label>
  );
}

export function SelectField({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: [value: string, label: string][];
}) {
  return (
    <Field label={label}>
      <select value={value} onChange={(e) => onChange(e.target.value)}>
        {options.map(([v, l]) => (
          <option key={v} value={v}>
            {l}
          </option>
        ))}
      </select>
    </Field>
  );
}

/** Up/down buttons; a missing handler disables its arrow. */
export function Arrows({ onUp, onDown }: { onUp?: () => void; onDown?: () => void }) {
  return (
    <span className="arrows">
      <button type="button" disabled={!onUp} aria-label={t("admin.up")} onClick={onUp}>
        ↑
      </button>
      <button type="button" disabled={!onDown} aria-label={t("admin.down")} onClick={onDown}>
        ↓
      </button>
    </span>
  );
}

/** Arrows for item `i` of `n` calling `move(direction)`. */
export const arrowsAt = (i: number, n: number, move: (d: "up" | "down") => void): ReactNode => (
  <Arrows onUp={i > 0 ? () => move("up") : undefined} onDown={i < n - 1 ? () => move("down") : undefined} />
);

/**
 * A guarded runner for a screen's actions: one at a time, errors reported (`handle` returns true
 * for the ones the screen shows itself), a success haptic unless the action returns false (a
 * declined confirmation).
 */
export function useAct(handle?: (e: unknown) => boolean) {
  const { busy, run } = useBusy();
  const act = (fn: () => Promise<void | false>) =>
    run(async () => {
      try {
        if ((await fn()) !== false) success();
      } catch (e) {
        if (!handle?.(e)) await report(e);
      }
    });
  return { busy, act };
}

/** The native «Save» button (`text` null hides it) running `save` through `useAct`. */
export function useSave(
  text: string | null,
  save: () => Promise<void | false>,
  handle?: (e: unknown) => boolean,
) {
  const { busy, act } = useAct(handle);
  useMainButton(text, () => act(save), { busy });
  return act;
}

/** Leave a form: back in the history, or to `fallback` when the app was opened right here. */
export function useExit(fallback: string) {
  const [, go] = useLocation();
  return () => (canGoBack() ? history.back() : go(fallback, { replace: true }));
}
