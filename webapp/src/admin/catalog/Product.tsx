import { useState } from "react";
import { useLocation } from "wouter";
import {
  ApiError,
  send,
  useFetch,
  type AdminCategory,
  type AdminProduct,
  type AdminService,
  type Fulfillment,
} from "../../api";
import { named, t } from "../../i18n";
import { confirm } from "../../telegram";
import { Failure, Field, Loading, Money, Row, Section, list } from "../../ui/kit";
import {
  compact,
  flag,
  fullI18n,
  I18nFields,
  pick,
  SelectField,
  SwitchRow,
  useExit,
  useSave,
} from "../kit";
import { SchemaEditor, schemaValid, toDrafts, toSchema } from "../SchemaEditor";
import { categoryOptions } from "./tree";

const TYPES: Fulfillment[] = ["stock", "fixed", "manual", "executor"];

/** `id` null: a new product in category `category`. */
export function ProductForm({ id, category }: { id: number | null; category: number }) {
  const cats = useFetch<AdminCategory[]>("/admin/categories");
  const services = useFetch<AdminService[]>("/admin/services");
  const product = useFetch<AdminProduct>(id === null ? null : `/admin/products/${id}`);
  const error = cats.error ?? services.error ?? product.error;
  if (error && !(cats.data && services.data && (id === null || product.data)))
    return <Failure error={error} retry={() => (cats.reload(), services.reload(), product.reload())} />;
  if (!cats.data || !services.data || (id !== null && !product.data)) return <Loading />;
  return <Editor cats={cats.data} services={services.data} product={product.data} category={category} />;
}

function Editor({
  cats,
  services,
  product,
  category,
}: {
  cats: AdminCategory[];
  services: AdminService[];
  product?: AdminProduct;
  category: number;
}) {
  const [, go] = useLocation();
  const [categoryId, setCategoryId] = useState(String(product?.category_id ?? category));
  const [type, setType] = useState<Fulfillment>(product?.fulfillment_type ?? "manual");
  const [serviceId, setServiceId] = useState(product?.service_id ? String(product.service_id) : "");
  const [title, setTitle] = useState(fullI18n(product?.title));
  const [description, setDescription] = useState(fullI18n(product?.description));
  const [text, setText] = useState(product?.fulfillment_config.text ?? "");
  const [active, setActive] = useState(product?.is_active ?? true);
  const [input, setInput] = useState(() => toDrafts(product?.input_schema ?? {}));
  const [result, setResult] = useState(() => toDrafts(product?.result_schema ?? {}));
  const [schemaError, setSchemaError] = useState<{ field: string; detail: string }>();
  const exit = useExit(`/admin/catalog/c/${categoryId}`);

  const executor = type === "executor";
  const valid =
    title.ru.trim() !== "" &&
    (!executor || serviceId !== "") &&
    (type !== "fixed" || text.trim() !== "") &&
    schemaValid(input) &&
    (!executor || schemaValid(result));

  const act = useSave(
    valid ? t("save") : null,
    async () => {
      setSchemaError(undefined);
      const body = {
        category_id: Number(categoryId),
        service_id: executor ? Number(serviceId) : null,
        title: compact(title),
        description: compact(description, true),
        fulfillment_type: type,
        fulfillment_config: type === "fixed" ? { text: text.trim() } : {},
        input_schema: toSchema(input),
        ...(executor && { result_schema: toSchema(result) }),
        is_active: active,
      };
      if (product) {
        await send("PATCH", `/admin/products/${product.id}`, body);
        exit();
      } else {
        const { id } = await send<{ id: number }>("POST", "/admin/products", body);
        go(`/admin/catalog/p/${id}`, { replace: true });
      }
    },
    (e) => {
      if (!(e instanceof ApiError) || (e.field !== "input_schema" && e.field !== "result_schema")) return false;
      setSchemaError({ field: e.field, detail: e.detail });
      return true;
    },
  );
  const remove = () =>
    act(async () => {
      if (!product || !(await confirm(t("product.deleteConfirm", { title: pick(product.title) })))) return false;
      await send("DELETE", `/admin/products/${product.id}`);
      go(`/admin/catalog/c/${product.category_id}`, { replace: true });
    });

  return (
    <div className="screen">
      <div className="headline">
        <h1>{product ? pick(product.title) : t("product.new")}</h1>
      </div>
      <Section footer={product?.used ? t(`product.used.${product.used}`) : undefined}>
        <SelectField
          label={t("product.category")}
          value={categoryId}
          onChange={setCategoryId}
          options={categoryOptions(cats)}
        />
        <I18nFields label={t("product.title")} value={title} invalid={!title.ru.trim()} onChange={setTitle} />
        <I18nFields label={t("product.description")} rows={3} value={description} onChange={setDescription} />
        <SelectField
          label={t("product.fulfillment")}
          value={type}
          onChange={(v) => setType(v as Fulfillment)}
          options={TYPES.map((x) => [x, named("fulfill", x)])}
        />
        {executor && (
          <SelectField
            label={t("product.service")}
            value={serviceId}
            onChange={setServiceId}
            options={[
              ["", t("product.noService")],
              ...services.map((s): [string, string] => [String(s.id), s.is_active ? s.title : `${s.title} (${t("admin.off")})`]),
            ]}
          />
        )}
        {type === "fixed" && (
          <Field label={t("product.fixedText")} invalid={!text.trim()}>
            <textarea rows={4} value={text} onChange={(e) => setText(e.target.value)} />
          </Field>
        )}
        <SwitchRow label={t("admin.active")} checked={active} onChange={setActive} />
      </Section>

      <SchemaEditor
        title={t("product.inputSchema")}
        footer={t("product.inputSchemaNote")}
        value={input}
        onChange={setInput}
        executorCanSee
        error={schemaError?.field === "input_schema" ? schemaError.detail : undefined}
      />
      {executor && (
        <SchemaEditor
          title={t("product.resultSchema")}
          footer={t("product.resultSchemaNote")}
          value={result}
          onChange={setResult}
          error={schemaError?.field === "result_schema" ? schemaError.detail : undefined}
        />
      )}

      {product && (
        <Section title={t("product.variantsTitle")} footer={t("product.variantsNote")}>
          {product.variants.map((v) => (
            <Row
              key={v.id}
              title={list(
                v.country_code ? `${flag(v.country_code)} ${v.country_code.toUpperCase()}` : t("variant.noCountry"),
                v.title ? pick(v.title) : null,
              )}
              sub={list(
                v.stock === null ? null : t("variant.stock", { n: v.stock }),
                v.is_active ? null : t("admin.off"),
              )}
              dim={!v.is_active}
              right={<Money value={v.price} />}
              chevron
              onClick={() => go(`/admin/catalog/p/${product.id}/v/${v.id}`)}
            />
          ))}
          <Row title={t("variant.add")} tone="link" onClick={() => go(`/admin/catalog/p/${product.id}/v/new`)} />
        </Section>
      )}
      {product && (
        <Section footer={t("product.deleteNote")}>
          <Row title={t("product.delete")} tone="bad" onClick={remove} />
        </Section>
      )}
    </div>
  );
}
