import { Link, useLocation } from "wouter";
import { t, type Key } from "../i18n";
import { sectionOf } from "../nav";
import { useUnread } from "../unread";
import { Badge } from "./kit";

const ICONS: Record<string, string> = {
  orders: "M5 6h14M5 12h14M5 18h9",
  balance: "M3.5 7.5h17v11h-17zM3.5 7.5l2.5-3h10l2 3M15.5 13h2",
  work: "M4 8.5h16v10H4zM9 8.5v-2h6v2M4 13h16",
  support: "M4 5.5h16v11H9.5L5 20v-3.5H4z",
};

export function Tabs({ tabs }: { tabs: { to: string; key: string }[] }) {
  const [path] = useLocation();
  const u = useUnread();
  const count: Record<string, number> = {
    orders: u.orders + u.support,
    work: u.work,
    support: u.tickets + u.review,
  };
  return (
    <nav className="tabs">
      {tabs.map(({ to, key }) => (
        <Link key={key} href={to} className={sectionOf(path) === key ? "on" : ""}>
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d={ICONS[key]} />
          </svg>
          {t(`tab.${key}` as Key)}
          <Badge n={count[key] ?? 0} />
        </Link>
      ))}
    </nav>
  );
}
