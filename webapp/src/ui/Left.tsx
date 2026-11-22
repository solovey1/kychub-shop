import { useEffect, useState } from "react";
import { t } from "../i18n";

/** A length of time: "15 мин", "2 ч", "1 ч 30 мин". */
export function duration(minutes: number) {
  const h = Math.floor(minutes / 60);
  if (!h) return t("left.m", { m: minutes });
  return minutes % 60 ? t("left.hm", { h, m: minutes % 60 }) : t("left.h", { h });
}

/** Time to a deadline, refreshed once a minute. */
export function Left({ until }: { until: string }) {
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 60_000);
    return () => clearInterval(timer);
  }, []);
  const minutes = Math.ceil((new Date(until).getTime() - now) / 60_000);
  if (minutes <= 0) return <span className="bad-text">{t("left.over")}</span>;
  const h = Math.floor(minutes / 60);
  return <>{h ? t("left.hm", { h, m: minutes % 60 }) : t("left.m", { m: minutes })}</>;
}
