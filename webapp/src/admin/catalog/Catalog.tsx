import { useState } from "react";
import { useLocation } from "wouter";
import {
  send,
  useFetch,
  type AdminCategory,
  type AdminCountry,
  type AdminProductBrief,
  type AdminService,
} from "../../api";
import { fmtMoney, named, t } from "../../i18n";
import { Empty, Failure, Loading, Row, Section, Segments, list } from "../../ui/kit";
import { arrowsAt, flag, pick, useAct } from "../kit";
import { childrenOf, pathTo } from "./tree";

export type CatalogSeg = "catalog" | "services" | "countries";
const PATH: Record<CatalogSeg, string> = {
  catalog: "/admin/catalog",
  services: "/admin/catalog/services",
  countries: "/admin/catalog/countries",
};

export function Catalog({ seg, cat }: { seg: CatalogSeg; cat?: number }) {
  const [, go] = useLocation();
  return (
    <div className="screen">
      <Segments
        value={seg}
        onChange={(s) => go(PATH[s], { replace: true })}
        items={[
          ["catalog", t("catalog.seg.catalog")],
          ["services", t("catalog.seg.services")],
          ["countries", t("catalog.seg.countries")],
        ]}
      />
      {seg === "catalog" && <Categories id={cat ?? null} />}
      {seg === "services" && <Services />}
      {seg === "countries" && <Countries />}
    </div>
  );
}

function Categories({ id }: { id: number | null }) {
  const [, go] = useLocation();
  const [ordering, setOrdering] = useState(false);
  const cats = useFetch<AdminCategory[]>("/admin/categories");
  const prods = useFetch<AdminProductBrief[]>(id === null ? null : `/admin/categories/${id}/products`);
  const { act } = useAct();

  if (cats.error && !cats.data) return <Failure error={cats.error} retry={cats.reload} />;
  if (!cats.data) return <Loading />;
  const current = id === null ? undefined : cats.data.find((c) => c.id === id);
  if (id !== null && !current) return <Empty text={t("error.notFound")} />;
  const kids = childrenOf(cats.data, id);
  const products = prods.data ?? [];

  const move = (kind: "categories" | "products", item: number, direction: "up" | "down") =>
    act(async () => {
      await send("POST", `/admin/${kind}/${item}/move`, { direction });
      cats.reload();
      prods.reload();
    });

  return (
    <>
      {current && (
        <div className="headline">
          <h1>{pick(current.title)}</h1>
          <p>{pathTo(cats.data, current.id).map((c) => pick(c.title)).join(" › ")}</p>
        </div>
      )}
      <Section title={t("catalog.categories")}>
        {kids.length === 0 && <Row title={t("catalog.noCategories")} />}
        {kids.map((c, i) => (
          <Row
            key={c.id}
            title={pick(c.title)}
            sub={
              list(
                c.children > 0 ? t("catalog.subcategories", { n: c.children }) : null,
                c.products > 0 ? t("catalog.products", { n: c.products }) : null,
              ) || t("catalog.emptyCategory")
            }
            dim={!c.is_active}
            right={
              ordering ? (
                arrowsAt(i, kids.length, (d) => move("categories", c.id, d))
              ) : c.is_active ? undefined : (
                <span className="off">{t("admin.off")}</span>
              )
            }
            chevron={!ordering}
            onClick={ordering ? undefined : () => go(`/admin/catalog/c/${c.id}`)}
          />
        ))}
        <Row
          title={t("catalog.addCategory")}
          tone="link"
          onClick={() => go(`/admin/catalog/c/new/in/${id ?? 0}`)}
        />
      </Section>
      {id !== null && (
        <Section title={t("catalog.productsTitle")}>
          {prods.data && products.length === 0 && <Row title={t("catalog.noProducts")} />}
          {products.map((p, i) => (
            <Row
              key={p.id}
              title={pick(p.title)}
              sub={list(
                named("fulfill", p.fulfillment_type),
                t("catalog.variants", { n: p.variants }),
                p.price_from && t("catalog.from", { sum: fmtMoney(p.price_from) }),
              )}
              dim={!p.is_active}
              right={
                ordering ? (
                  arrowsAt(i, products.length, (d) => move("products", p.id, d))
                ) : p.is_active ? undefined : (
                  <span className="off">{t("admin.off")}</span>
                )
              }
              chevron={!ordering}
              onClick={ordering ? undefined : () => go(`/admin/catalog/p/${p.id}`)}
            />
          ))}
          <Row title={t("catalog.addProduct")} tone="link" onClick={() => go(`/admin/catalog/p/new/in/${id}`)} />
        </Section>
      )}
      <Section>
        {(kids.length > 1 || products.length > 1) && (
          <Row
            title={ordering ? t("catalog.orderDone") : t("catalog.order")}
            tone="link"
            onClick={() => setOrdering(!ordering)}
          />
        )}
        {current && (
          <Row title={t("catalog.editCategory")} chevron onClick={() => go(`/admin/catalog/c/${current.id}/edit`)} />
        )}
      </Section>
    </>
  );
}

function Services() {
  const [, go] = useLocation();
  const { data, error, reload } = useFetch<AdminService[]>("/admin/services");
  if (error && !data) return <Failure error={error} retry={reload} />;
  if (!data) return <Loading />;
  return (
    <Section>
      {data.length === 0 && <Row title={t("catalog.noServices")} />}
      {data.map((s) => (
        <Row
          key={s.id}
          title={s.title}
          sub={list(
            s.code,
            t("catalog.minutes", { n: s.deadline_minutes }),
            named("service.mode", s.assign_mode),
            `${s.executor_percent}%`,
          )}
          dim={!s.is_active}
          right={s.is_active ? undefined : <span className="off">{t("admin.off")}</span>}
          chevron
          onClick={() => go(`/admin/catalog/s/${s.id}`)}
        />
      ))}
      <Row title={t("catalog.addService")} tone="link" onClick={() => go("/admin/catalog/s/new")} />
    </Section>
  );
}

function Countries() {
  const [, go] = useLocation();
  const { data, error, reload } = useFetch<AdminCountry[]>("/admin/countries");
  if (error && !data) return <Failure error={error} retry={reload} />;
  if (!data) return <Loading />;
  return (
    <Section>
      {data.length === 0 && <Row title={t("catalog.noCountries")} />}
      {data.map((c) => (
        <Row
          key={c.code}
          title={`${flag(c.code)} ${pick(c.title)}`}
          sub={c.code.toUpperCase()}
          chevron
          onClick={() => go(`/admin/catalog/k/${c.code}`)}
        />
      ))}
      <Row title={t("catalog.addCountry")} tone="link" onClick={() => go("/admin/catalog/k/new")} />
    </Section>
  );
}
