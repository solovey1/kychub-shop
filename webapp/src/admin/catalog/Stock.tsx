import { useState } from "react";
import { send, useFetch, type AdminProduct, type AdminStock } from "../../api";
import { t } from "../../i18n";
import { confirm } from "../../telegram";
import { Failure, Field, Loading, Row, Section } from "../../ui/kit";
import { pick, useAct, useSave } from "../kit";

type Imported = { added: number; duplicates: number };

const oneLine = (payload: string) => {
  const line = payload.split("\n")[0];
  return line.length > 60 ? `${line.slice(0, 60)}…` : line;
};

export function Stock({ pid, id }: { pid: number; id: number }) {
  const stock = useFetch<AdminStock>(`/admin/variants/${id}/stock`);
  const product = useFetch<AdminProduct>(`/admin/products/${pid}`);
  const error = stock.error ?? product.error;
  if (error && !(stock.data && product.data))
    return <Failure error={error} retry={() => (stock.reload(), product.reload())} />;
  if (!stock.data || !product.data) return <Loading />;
  const variant = product.data.variants.find((v) => v.id === id);
  return (
    <Editor
      id={id}
      stock={stock.data}
      reload={stock.reload}
      subtitle={`${pick(product.data.title)}${variant?.title ? ` · ${pick(variant.title)}` : ""}`}
    />
  );
}

function Editor({
  id,
  stock,
  reload,
  subtitle,
}: {
  id: number;
  stock: AdminStock;
  reload: () => void;
  subtitle: string;
}) {
  const [text, setText] = useState("");
  const [unlimited, setUnlimited] = useState(stock.unlimited ?? "");
  const [imported, setImported] = useState<Imported>();
  const { act } = useAct();

  useSave(text.trim() ? t("stock.addButton") : null, async () => {
    setImported(await send<Imported>("POST", `/admin/variants/${id}/stock`, { text }));
    setText("");
    reload();
  });
  const saveUnlimited = () =>
    act(async () => {
      await send("PUT", `/admin/variants/${id}/stock/unlimited`, { text: unlimited.trim() || null });
      reload();
    });
  const remove = (unit: number) =>
    act(async () => {
      if (!(await confirm(t("stock.deleteConfirm")))) return false;
      await send("DELETE", `/admin/stock/${unit}`);
      reload();
    });

  return (
    <div className="screen">
      <div className="headline">
        <h1>{t("stock.free", { n: stock.free })}</h1>
        <p>{subtitle}</p>
      </div>
      <Section footer={t("stock.addNote")}>
        <Field label={t("stock.add")}>
          <textarea rows={6} value={text} autoCapitalize="none" onChange={(e) => setText(e.target.value)} />
        </Field>
        {imported && <Row title={t("stock.result", { added: imported.added, skipped: imported.duplicates })} />}
      </Section>
      <Section title={t("stock.unlimited")} footer={t("stock.unlimitedNote")}>
        <Field label={t("stock.unlimitedLabel")}>
          <textarea
            rows={3}
            value={unlimited}
            autoCapitalize="none"
            onChange={(e) => setUnlimited(e.target.value)}
          />
        </Field>
        <Row title={t("save")} tone="link" onClick={saveUnlimited} />
      </Section>
      <Section title={t("stock.recent")}>
        {stock.recent.length === 0 && <Row title={t("stock.none")} />}
        {stock.recent.map((u) => (
          <Row
            key={u.id}
            title={oneLine(u.payload)}
            right={
              <button className="bad-text" onClick={() => remove(u.id)}>
                {t("admin.delete")}
              </button>
            }
          />
        ))}
      </Section>
    </div>
  );
}
