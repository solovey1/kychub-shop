import { useState } from "react";
import { useLocation } from "wouter";
import { send, useFetch, type UserBrief, type UserCard } from "../../api";
import { cents, fmtDate, fmtMoney, named, t } from "../../i18n";
import { confirm } from "../../telegram";
import { Failure, Field, Loading, Money, Row, Section, list } from "../../ui/kit";
import { allowed } from "../access";
import { SwitchRow, useAct, useSave } from "../kit";
import { roleList } from "./People";

const FLAGS = ["manager", "can_catalog", "can_finance", "can_users", "can_broadcast"];
const AMOUNT = /^-?\d{1,8}(\.\d{1,2})?$/;

export function UserScreen({ id, viewer }: { id: number; viewer: string[] }) {
  const { data, error, reload } = useFetch<UserCard>(`/admin/users/${id}`);
  if (error && !data) return <Failure error={error} retry={reload} />;
  if (!data) return <Loading />;
  return <Card user={data} viewer={viewer} />;
}

function Card({ user, viewer }: { user: UserCard; viewer: string[] }) {
  const [, go] = useLocation();
  const [roles, setRoles] = useState(user.roles);
  const { act } = useAct();
  const admin = allowed(viewer, "admin");
  const protectedUser = roles.includes("admin") || roles.includes("owner");

  const toggle = (flag: string, on: boolean) =>
    act(async () => {
      const r = await send<UserBrief>("PUT", `/admin/users/${user.id}/roles`, { flags: { [flag]: on } });
      setRoles(r.roles);
    });
  const removeManager = () =>
    act(async () => {
      if (!(await confirm(t("people.removeConfirm", { name: user.name })))) return false;
      await send("DELETE", `/admin/managers/${user.id}`);
      setRoles(roles.filter((r) => r !== "manager"));
    });

  return (
    <div className="screen">
      <div className="headline">
        <h1>{user.name}</h1>
        <p>{list(`ID ${user.id}`, user.blocked ? t("people.blocked") : null)}</p>
      </div>
      <Section>
        <Row title={t("people.language")} right={user.language.toUpperCase()} />
        <Row title={t("people.registered")} right={fmtDate(user.created_at)} />
        <Row title={t("people.roles")} right={roleList(roles) || t("none")} />
      </Section>

      {user.balance !== null && <Balance id={user.id} start={user.balance} />}

      {admin && (
        <Section title={t("people.rights")} footer={protectedUser ? t("conflict.protected") : undefined}>
          {!protectedUser &&
            FLAGS.map((f) => (
              <SwitchRow key={f} label={named("role", f)} checked={roles.includes(f)} onChange={(on) => toggle(f, on)} />
            ))}
          {protectedUser && <Row title={roleList(roles)} />}
        </Section>
      )}
      {admin && !protectedUser && roles.includes("manager") && (
        <Section>
          <Row title={t("people.removeManager")} tone="bad" onClick={removeManager} />
        </Section>
      )}

      <Section title={t("people.orders")}>
        {user.orders.length === 0 && <Row title={t("people.noOrders")} />}
        {user.orders.map((o) => (
          <Row
            key={o.id}
            title={o.product}
            sub={list(`№${o.id}`, named("status", o.status), fmtDate(o.created_at))}
            right={<Money value={o.total} />}
            chevron={allowed(viewer, "staff")}
            onClick={allowed(viewer, "staff") ? () => go(`/admin/orders/${o.id}`) : undefined}
          />
        ))}
      </Section>
    </div>
  );
}

/** One token per form: a retry after a lost answer posts once; a new one after a success. */
function Balance({ id, start }: { id: number; start: string }) {
  const [balance, setBalance] = useState(start);
  const [amount, setAmount] = useState("");
  const [comment, setComment] = useState("");
  const [token, setToken] = useState(() => crypto.randomUUID());
  const valid = AMOUNT.test(amount.trim()) && cents(amount.trim().replace("-", "")) > 0n && comment.trim() !== "";
  const sum = amount.trim();

  useSave(valid ? t("people.apply") : null, async () => {
    if (!(await confirm(t("people.applyConfirm", { sum: fmtMoney(sum, true), comment: comment.trim() })))) return false;
    const r = await send<{ balance: string }>("POST", `/admin/users/${id}/balance`, {
      amount: sum,
      comment: comment.trim(),
      token,
    });
    setBalance(r.balance);
    setAmount("");
    setComment("");
    setToken(crypto.randomUUID());
  });

  return (
    <>
      <div className="hero">
        <p className="caption">{t("people.balance")}</p>
        <Money value={balance} big />
      </div>
      <Section title={t("people.adjust")} footer={t("people.adjustNote")}>
        <Field label={t("people.amount")} invalid={amount !== "" && !AMOUNT.test(sum)}>
          <input
            inputMode="decimal"
            value={amount}
            onChange={(e) => setAmount(e.target.value.replace(",", ".").replace(/[^0-9.-]/g, ""))}
          />
        </Field>
        <Field label={t("people.comment")}>
          <input value={comment} maxLength={200} onChange={(e) => setComment(e.target.value)} />
        </Field>
      </Section>
    </>
  );
}
