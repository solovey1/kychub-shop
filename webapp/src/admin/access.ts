import type { Key } from "../i18n";
import type { PATHS } from "../ui/Icon";

type Perm = "catalog" | "finance" | "users" | "broadcast" | "admin" | "staff-finance" | "staff";

export type Section = {
  id: string;
  path: string;
  icon: keyof typeof PATHS;
  titleKey: Key;
  descKey: Key;
  perm: Perm;
  /** has a screen; flip it when the section is built */
  ready: boolean;
};

export const SECTIONS: Section[] = [
  { id: "catalog", path: "/admin/catalog", icon: "catalog", titleKey: "admin.catalog", descKey: "admin.catalog.desc", perm: "catalog", ready: true },
  { id: "people", path: "/admin/people", icon: "people", titleKey: "admin.people", descKey: "admin.people.desc", perm: "users", ready: true },
  { id: "orders", path: "/admin/orders", icon: "receipt", titleKey: "admin.orders", descKey: "admin.orders.desc", perm: "staff", ready: true },
  { id: "money", path: "/admin/money", icon: "money", titleKey: "admin.money", descKey: "admin.money.desc", perm: "finance", ready: true },
  { id: "promo", path: "/admin/promo", icon: "promo", titleKey: "admin.promo", descKey: "admin.promo.desc", perm: "finance", ready: true },
  { id: "broadcasts", path: "/admin/broadcasts", icon: "broadcasts", titleKey: "admin.broadcasts", descKey: "admin.broadcasts.desc", perm: "broadcast", ready: true },
  { id: "stats", path: "/admin/stats", icon: "stats", titleKey: "admin.stats", descKey: "admin.stats.desc", perm: "staff-finance", ready: true },
  { id: "settings", path: "/admin/settings", icon: "settings", titleKey: "admin.settings", descKey: "admin.settings.desc", perm: "admin", ready: true },
  { id: "audit", path: "/admin/audit", icon: "audit", titleKey: "admin.audit", descKey: "admin.audit.desc", perm: "admin", ready: true },
];

const isAdmin = (roles: string[]) => roles.includes("admin") || roles.includes("owner");

/** Roles come from GET /me as lowercase names; admins and owners see everything. */
export function allowed(roles: string[], perm: Perm): boolean {
  if (isAdmin(roles)) return true;
  switch (perm) {
    case "admin":
      return false;
    case "staff":
      return roles.includes("manager");
    case "staff-finance":
      return roles.includes("can_finance");
    default:
      return roles.includes(`can_${perm}`);
  }
}

export const visibleSections = (roles: string[]) =>
  SECTIONS.filter((s) => s.ready && allowed(roles, s.perm));

/** The Admin tab is for anyone with an admin right, even before their section is built. */
export const hasAdminTab = (roles: string[]) => isAdmin(roles) || roles.includes("manager") || roles.some((r) => r.startsWith("can_"));
