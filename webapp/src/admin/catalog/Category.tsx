import { useState } from "react";
import { useLocation } from "wouter";
import { ApiError, send, useFetch, type AdminCategory } from "../../api";
import { t } from "../../i18n";
import { confirm } from "../../telegram";
import { Failure, Loading, Row, Section } from "../../ui/kit";
import { compact, fullI18n, I18nFields, pick, SelectField, SwitchRow, useExit, useSave } from "../kit";
import { categoryOptions } from "./tree";

/** `id` null: a new category under `parent` (null: at the root). */
export function CategoryForm({ id, parent }: { id: number | null; parent: number | null }) {
  const { data, error, reload } = useFetch<AdminCategory[]>("/admin/categories");
  if (error && !data) return <Failure error={error} retry={reload} />;
  if (!data) return <Loading />;
  const current = id === null ? undefined : data.find((c) => c.id === id);
  if (id !== null && !current) return <Failure error={new ApiError(404, null, "")} />;
  return <Editor all={data} current={current} parent={current ? current.parent_id : parent} />;
}

function Editor({
  all,
  current,
  parent,
}: {
  all: AdminCategory[];
  current?: AdminCategory;
  parent: number | null;
}) {
  const [, go] = useLocation();
  const [title, setTitle] = useState(fullI18n(current?.title));
  const [parentId, setParentId] = useState(parent === null ? "" : String(parent));
  const [active, setActive] = useState(current?.is_active ?? true);
  const exit = useExit(current ? `/admin/catalog/c/${current.id}` : "/admin/catalog");

  const body = {
    parent_id: parentId === "" ? null : Number(parentId),
    title: compact(title),
    is_active: active,
  };
  const act = useSave(title.ru.trim() ? t("save") : null, async () => {
    if (current) {
      await send("PATCH", `/admin/categories/${current.id}`, body);
      exit();
    } else {
      const { id } = await send<{ id: number }>("POST", "/admin/categories", body);
      go(`/admin/catalog/c/${id}`, { replace: true });
    }
  });
  const remove = () =>
    act(async () => {
      if (!current || !(await confirm(t("category.deleteConfirm", { title: pick(current.title) })))) return false;
      await send("DELETE", `/admin/categories/${current.id}`);
      go(current.parent_id === null ? "/admin/catalog" : `/admin/catalog/c/${current.parent_id}`, { replace: true });
    });

  return (
    <div className="screen">
      <div className="headline">
        <h1>{current ? pick(current.title) : t("category.new")}</h1>
      </div>
      <Section>
        <I18nFields label={t("category.title")} value={title} invalid={!title.ru.trim()} onChange={setTitle} />
        <SelectField
          label={t("category.parent")}
          value={parentId}
          onChange={setParentId}
          options={[["", t("category.root")], ...categoryOptions(all, current?.id)]}
        />
        <SwitchRow label={t("admin.active")} checked={active} onChange={setActive} />
      </Section>
      {current && (
        <Section footer={t("category.deleteNote")}>
          <Row title={t("category.delete")} tone="bad" onClick={remove} />
        </Section>
      )}
    </div>
  );
}
