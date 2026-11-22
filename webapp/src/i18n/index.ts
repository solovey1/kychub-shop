import { en } from "./en";
import { ru } from "./ru";
import { uk } from "./uk";

export type Key = keyof typeof ru;
const dicts = { ru, en, uk };
type Lang = keyof typeof dicts;

let lang: Lang = "en";

export function setLang(code: string | undefined) {
  lang = code?.startsWith("ru") ? "ru" : code?.startsWith("uk") ? "uk" : "en";
}
export const getLang = () => lang;

const PLURALS = ["one", "few", "many", "other"];

/** `{name}` is substituted; a value with `|` holds plural forms (one|few|many|other, or one|other)
 * and is picked by `n`. */
export function t(key: Key, params: Record<string, string | number> = {}): string {
  let text = dicts[lang][key];
  if (text.includes("|")) {
    const forms = text.split("|");
    const order = forms.length === 2 ? ["one", "other"] : PLURALS;
    const at = order.indexOf(new Intl.PluralRules(lang).select(Number(params.n)));
    text = forms[at < 0 ? forms.length - 1 : at];
  }
  return text.replace(/\{(\w+)\}/g, (_, k: string) => String(params[k] ?? ""));
}

export const known = (key: string): key is Key => key in ru;

/** A dictionary entry by a name that comes from the server (status, ledger kind, role). */
export function named(prefix: string, name: string): string {
  const key = `${prefix}.${name}`;
  return key in ru ? t(key as Key) : name;
}

/** Money is a string and stays one: split the sign, group the integer part, never a float. */
export function moneyParts(value: string, signed = false) {
  const negative = value.startsWith("-");
  const [int = "0", frac = ""] = value.replace(/^[-+]/, "").split(".");
  return {
    sign: negative ? "−" : signed && /[1-9]/.test(value) ? "+" : "",
    negative,
    num: `${int.replace(/\B(?=(\d{3})+(?!\d))/g, " ")}.${frac.padEnd(2, "0")}`,
  };
}

export function fmtMoney(value: string, signed = false) {
  const { sign, num } = moneyParts(value, signed);
  return `${sign}$${num}`;
}

const isToday = (d: Date) => d.toDateString() === new Date().toDateString();

export function fmtDate(iso: string, timeOnlyToday = false) {
  const d = new Date(iso);
  const opts: Intl.DateTimeFormatOptions =
    timeOnlyToday && isToday(d)
      ? { hour: "2-digit", minute: "2-digit" }
      : { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" };
  return new Intl.DateTimeFormat(lang, opts).format(d);
}

/** `2026-11-25` (a calendar date, no zone) as `25.11`. */
export const fmtDay = (iso: string) => iso.slice(8, 10) + "." + iso.slice(5, 7);

/** Money as whole cents for comparing, never a float. */
export function cents(value: string): bigint {
  const [int = "0", frac = ""] = value.split(".");
  return BigInt(int + frac.padEnd(2, "0").slice(0, 2));
}
