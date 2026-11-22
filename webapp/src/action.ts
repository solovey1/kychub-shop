import { useCallback, useRef, useState } from "react";
import { ApiError } from "./api";
import { known, t } from "./i18n";
import { alert, failure } from "./telegram";

/** What went wrong and what to do, for a person. */
export function reason(e: unknown): string {
  if (!(e instanceof ApiError)) return t("error.network");
  if (e.status === 404) return t("error.notFound");
  if (e.status === 409) {
    const key = `conflict.${e.code}`;
    return known(key) ? t(key) : t("error.conflict");
  }
  if (e.status === 400 || e.status === 422) return t("error.rejected", { detail: e.detail });
  return t("error.generic");
}

export function report(e: unknown) {
  failure();
  return alert(reason(e));
}

/** One action at a time: a second tap while the first request is running does nothing. */
export function useBusy() {
  const [busy, setBusy] = useState(false);
  const flag = useRef(false);
  const run = useCallback(async (fn: () => Promise<unknown>) => {
    if (flag.current) return;
    flag.current = true;
    setBusy(true);
    try {
      await fn();
    } finally {
      flag.current = false;
      setBusy(false);
    }
  }, []);
  return { busy, run };
}
