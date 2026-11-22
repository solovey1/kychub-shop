import { useEffect, useState } from "react";
import { useLocation } from "wouter";
import { get, send, useFetch, type ApiError, type ExecutorRow, type UserBrief } from "../../api";
import { named, t } from "../../i18n";
import { Empty, Failure, Field, Loading, Row, Section, Segments, list } from "../../ui/kit";
import { allowed } from "../access";
import { useAct } from "../kit";

export type PeopleSeg = "users" | "executors" | "managers";
const PATH: Record<PeopleSeg, string> = {
  users: "/admin/people",
  executors: "/admin/people/executors",
  managers: "/admin/people/managers",
};

/** The roles a person holds besides plain buyer, as text. */
export const roleList = (roles: string[]) => roles.map((r) => named("role", r)).join(", ");

export function People({ seg, roles }: { seg: PeopleSeg; roles: string[] }) {
  const [, go] = useLocation();
  return (
    <div className="screen">
      <Segments
        value={seg}
        onChange={(s) => go(PATH[s], { replace: true })}
        items={[
          ["users", t("people.seg.users")],
          ["executors", t("people.seg.executors")],
          ["managers", t("people.seg.managers")],
        ]}
      />
      {seg === "users" && <Users />}
      {seg === "executors" && <Executors />}
      {seg === "managers" && <Managers admin={allowed(roles, "admin")} />}
    </div>
  );
}

function Users() {
  const [, go] = useLocation();
  const [query, setQuery] = useState("");
  const [found, setFound] = useState<UserBrief[]>();
  const [error, setError] = useState<ApiError>();
  useEffect(() => {
    const q = query.trim();
    if (!q) {
      setFound(undefined);
      return;
    }
    let stale = false;
    const timer = setTimeout(
      () =>
        get<UserBrief[]>(`/admin/users?q=${encodeURIComponent(q)}`).then(
          (r) => !stale && (setFound(r), setError(undefined)),
          (e: ApiError) => !stale && setError(e),
        ),
      300,
    );
    return () => {
      stale = true;
      clearTimeout(timer);
    };
  }, [query]);
  return (
    <>
      <Section footer={t("people.searchNote")}>
        <Field label={t("people.search")}>
          <input value={query} autoCapitalize="none" onChange={(e) => setQuery(e.target.value)} />
        </Field>
      </Section>
      {error && <Failure error={error} />}
      {found?.length === 0 && <Empty text={t("people.notFound")} />}
      {found && found.length > 0 && (
        <Section>
          {found.map((u) => (
            <Row
              key={u.id}
              title={u.name}
              sub={list(String(u.id), roleList(u.roles))}
              chevron
              onClick={() => go(`/admin/people/u/${u.id}`)}
            />
          ))}
        </Section>
      )}
    </>
  );
}

function Executors() {
  const [, go] = useLocation();
  const { data, error, reload } = useFetch<ExecutorRow[]>("/admin/executors");
  if (error && !data) return <Failure error={error} retry={reload} />;
  if (!data) return <Loading />;
  return (
    <Section>
      {data.length === 0 && <Row title={t("people.noExecutors")} />}
      {data.map((e) => (
        <Row
          key={e.id}
          title={e.alias}
          sub={t("people.executorRow", {
            work: e.in_work,
            done: e.completed,
            score: e.avg_score === null ? t("none") : e.avg_score.toFixed(1),
          })}
          dim={!e.is_active}
          right={e.is_active ? undefined : <span className="off">{t("admin.off")}</span>}
          chevron
          onClick={() => go(`/admin/people/e/${e.id}`)}
        />
      ))}
      <Row title={t("people.addExecutor")} tone="link" onClick={() => go("/admin/people/e/new")} />
    </Section>
  );
}

function Managers({ admin }: { admin: boolean }) {
  const [, go] = useLocation();
  const [tgId, setTgId] = useState("");
  const { data, error, reload } = useFetch<UserBrief[]>("/admin/managers");
  const { act } = useAct();
  const add = () =>
    act(async () => {
      await send("POST", "/admin/managers", { tg_id: Number(tgId) });
      setTgId("");
      reload();
    });
  if (error && !data) return <Failure error={error} retry={reload} />;
  if (!data) return <Loading />;
  return (
    <>
      <Section>
        {data.length === 0 && <Row title={t("people.noManagers")} />}
        {data.map((m) => (
          <Row
            key={m.id}
            title={m.name}
            sub={list(String(m.id), roleList(m.roles.filter((r) => r.startsWith("can_"))))}
            chevron
            onClick={() => go(`/admin/people/u/${m.id}`)}
          />
        ))}
      </Section>
      {admin && (
        <Section footer={t("people.addManagerNote")}>
          <Field label={t("people.tgId")}>
            <input inputMode="numeric" value={tgId} onChange={(e) => setTgId(e.target.value.replace(/\D/g, ""))} />
          </Field>
          {tgId !== "" && <Row title={t("people.addManager")} tone="link" onClick={add} />}
        </Section>
      )}
    </>
  );
}
