import { useState } from "react";
import { useLocation } from "wouter";
import { ApiError, send, useFetch, type AdminCountry, type AdminProduct, type AdminVariant } from "../../api";
import { t } from "../../i18n";
import { confirm } from "../../telegram";
import { Failure, Field, Loading, Row, Section } from "../../ui/kit";
import { compact, flag, fullI18n, I18nFields, pick, SelectField, SwitchRow, useExit, useSave } from "../kit";

const PRICE = /^\d{1,8}(\.\d{1,2})?$/;

/** `id` null: a new variant of product `pid`. */
export function VariantForm({ pid, id }: { pid: number; id: number | null }) {
  const product = useFetch<AdminProduct>(`/admin/products/${pid}`);
  const countries = useFetch<AdminCountry[]>("/admin/countries");
  const error = product.error ?? countries.error;
  if (error && !(product.data && countries.data))
    return <Failure error={error} retry={() => (product.reload(), countries.reload())} />;
  if (!product.data || !countries.data) return <Loading />;
  const variant = id === null ? undefined : product.data.variants.find((v) => v.id === id);
  if (id !== null && !variant) return <Failure error={new ApiError(404, null, "")} />;
  return <Editor product={product.data} countries={countries.data} variant={variant} />;
}

function Editor({
  product,
  countries,
  variant,
}: {
  product: AdminProduct;
  countries: AdminCountry[];
  variant?: AdminVariant;
}) {
  const [, go] = useLocation();
  const [price, setPrice] = useState(variant?.price ?? "");
  const [country, setCountry] = useState(variant?.country_code ?? "");
  const [title, setTitle] = useState(fullI18n(variant?.title));
  const [active, setActive] = useState(variant?.is_active ?? true);
  const exit = useExit(`/admin/catalog/p/${product.id}`);
  const stock = product.fulfillment_type === "stock";

  const act = useSave(PRICE.test(price.trim()) ? t("save") : null, async () => {
    const body = {
      country_code: country || null,
      title: Object.values(title).some((s) => s.trim()) ? compact(title, true) : null,
      price: price.trim(),
      is_active: active,
    };
    if (variant) {
      await send("PATCH", `/admin/variants/${variant.id}`, body);
      exit();
    } else {
      const { id } = await send<{ id: number }>("POST", `/admin/products/${product.id}/variants`, body);
      // a stock product goes on to fill its stock
      if (stock) go(`/admin/catalog/p/${product.id}/v/${id}`, { replace: true });
      else exit();
    }
  });
  const remove = () =>
    act(async () => {
      if (!variant || !(await confirm(t("variant.deleteConfirm")))) return false;
      await send("DELETE", `/admin/variants/${variant.id}`);
      go(`/admin/catalog/p/${product.id}`, { replace: true });
    });

  return (
    <div className="screen">
      <div className="headline">
        <h1>{variant ? t("variant.title") : t("variant.new")}</h1>
        <p>{pick(product.title)}</p>
      </div>
      <Section>
        <Field label={t("variant.price")} invalid={price !== "" && !PRICE.test(price.trim())}>
          <input inputMode="decimal" value={price} onChange={(e) => setPrice(e.target.value.replace(",", "."))} />
        </Field>
        <SelectField
          label={t("variant.country")}
          value={country}
          onChange={setCountry}
          options={[
            ["", t("variant.noCountry")],
            ...countries.map((c): [string, string] => [c.code, `${flag(c.code)} ${pick(c.title)}`]),
          ]}
        />
        <I18nFields label={t("variant.titleOptional")} value={title} onChange={setTitle} />
        <SwitchRow label={t("admin.active")} checked={active} onChange={setActive} />
      </Section>
      {variant && stock && (
        <Section>
          <Row
            title={t("variant.stockLink")}
            right={t("variant.stock", { n: variant.stock ?? 0 })}
            chevron
            onClick={() => go(`/admin/catalog/p/${product.id}/v/${variant.id}/stock`)}
          />
        </Section>
      )}
      {variant && (
        <Section footer={t("variant.deleteNote")}>
          <Row title={t("variant.delete")} tone="bad" onClick={remove} />
        </Section>
      )}
    </div>
  );
}
