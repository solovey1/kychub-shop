import { Link, useLocation } from "wouter";
import { t, type Key } from "../i18n";
import { sectionOf } from "../nav";
import { useUnread } from "../unread";
import { Icon, type PATHS } from "./Icon";
import { Badge } from "./kit";

export function Tabs({ tabs }: { tabs: { to: string; key: string }[] }) {
  const [path] = useLocation();
  const u = useUnread();
  const count: Record<string, number> = {
    orders: u.orders + u.support,
    work: u.work,
    support: u.tickets + u.review + u.disputes,
  };
  return (
    <nav className="tabs">
      {tabs.map(({ to, key }) => (
        <Link key={key} href={to} className={sectionOf(path) === key ? "on" : ""}>
          <Icon name={key as keyof typeof PATHS} />
          {t(key === "admin" ? "tab.manage" : (`tab.${key}` as Key))}
          <Badge n={count[key] ?? 0} />
        </Link>
      ))}
    </nav>
  );
}
