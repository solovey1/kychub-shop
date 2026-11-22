import type { ReactNode } from "react";
import { ApiError } from "../api";
import { moneyParts, t } from "../i18n";
import { close } from "../telegram";

export function Section({
  title,
  footer,
  children,
}: {
  title?: string;
  footer?: string;
  children: ReactNode;
}) {
  return (
    <section className="section">
      {title && <h2>{title}</h2>}
      <div className="group">{children}</div>
      {footer && <p className="footer">{footer}</p>}
    </section>
  );
}

/** Unread count: a filled circle, `99+` past two digits, nothing for zero. */
export function Badge({ n }: { n: number }) {
  return n > 0 ? <span className="badge">{n > 99 ? "99+" : n}</span> : null;
}

/** Status colour in lists: red only when the order went wrong, muted when it was cancelled. */
export const statusTone = (status: string) =>
  status === "failed" || status === "refunded" ? "bad-text" : status === "cancelled" ? "hint" : "";

export function Row({
  title,
  sub,
  meta,
  right,
  rightSub,
  tone,
  chevron,
  unread,
  dim,
  icon,
  onClick,
}: {
  title: ReactNode;
  sub?: ReactNode;
  meta?: ReactNode;
  right?: ReactNode;
  rightSub?: ReactNode;
  tone?: "bad" | "link";
  chevron?: boolean;
  unread?: number;
  dim?: boolean;
  icon?: ReactNode;
  onClick?: () => void;
}) {
  const Tag = onClick ? "button" : "div";
  return (
    <Tag className={`row${tone ? ` tone-${tone}` : ""}${dim ? " dim" : ""}`} onClick={onClick}>
      {icon && <span className="row-icon">{icon}</span>}
      <span className="row-main">
        <span className="row-title">
          {title}
          <Badge n={unread ?? 0} />
        </span>
        {sub && <span className="row-sub">{sub}</span>}
        {meta && <span className="row-sub">{meta}</span>}
      </span>
      {(right || rightSub) && (
        <span className="row-right">
          {right}
          {rightSub && <span className="row-sub">{rightSub}</span>}
        </span>
      )}
      {chevron && <i className="chevron" />}
    </Tag>
  );
}

/** An amount: «$12.50», a debit «−$3.00» with a real minus; a credit is green when `signed`. */
export function Money({
  value,
  signed,
  big,
}: {
  value: string;
  signed?: boolean;
  big?: boolean;
}) {
  const { sign, negative, num } = moneyParts(value, signed);
  const credit = signed && sign === "+";
  return (
    <span className={`money${big ? " big" : ""}${credit ? " credit" : ""}${negative ? " debit" : ""}`}>
      {sign}
      <span className="cur">$</span>
      {num}
    </span>
  );
}

export function Segments<K extends string>({
  value,
  items,
  onChange,
  small,
}: {
  value: K;
  items: [K, ReactNode][];
  onChange: (key: K) => void;
  small?: boolean;
}) {
  return (
    <div className={`segments${small ? " small" : ""}`} role="tablist">
      {items.map(([key, label]) => (
        <button
          key={key}
          role="tab"
          aria-selected={key === value}
          className={key === value ? "on" : ""}
          onClick={() => onChange(key)}
        >
          {label}
        </button>
      ))}
    </div>
  );
}

export const Empty = ({ text }: { text: string }) => <p className="empty">{text}</p>;
export const Loading = () => <p className="empty">{t("loading")}</p>;

export function Failure({ error, retry }: { error: ApiError; retry?: () => void }) {
  return (
    <div className="empty">
      <p>{error.status === 404 ? t("error.notFound") : t("error.generic")}</p>
      {retry && error.status !== 404 && (
        <button className="link" onClick={retry}>
          {t("retry")}
        </button>
      )}
    </div>
  );
}

export function Hint({ title, text, action }: { title: string; text: string; action?: boolean }) {
  return (
    <div className="center">
      <h1>{title}</h1>
      <p>{text}</p>
      {action && (
        <button className="link" onClick={close}>
          {t("close")}
        </button>
      )}
    </div>
  );
}

export function Field({
  label,
  invalid,
  error,
  children,
}: {
  label: string;
  invalid?: boolean;
  error?: string;
  children: ReactNode;
}) {
  return (
    <div className={`field${invalid ? " invalid" : ""}`}>
      <label>{label}</label>
      {children}
      {error && <span className="error">{error}</span>}
    </div>
  );
}

export const list = (...parts: (string | null | undefined)[]) => parts.filter(Boolean).join(", ");
