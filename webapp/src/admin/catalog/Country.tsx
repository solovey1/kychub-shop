import { useState } from "react";
import { useLocation } from "wouter";
import { ApiError, send, useFetch, type AdminCountry } from "../../api";
import { t } from "../../i18n";
import { confirm } from "../../telegram";
import { Failure, Field, Loading, Row, Section } from "../../ui/kit";
import { compact, flag, fullI18n, I18nFields, pick, useExit, useSave } from "../kit";

/** `code` null: a new country. */
export function CountryForm({ code }: { code: string | null }) {
  const { data, error, reload } = useFetch<AdminCountry[]>("/admin/countries");
  if (error && !data) return <Failure error={error} retry={reload} />;
  if (!data) return <Loading />;
  const country = code === null ? undefined : data.find((c) => c.code === code);
  if (code !== null && !country) return <Failure error={new ApiError(404, null, "")} />;
  return <Editor country={country} />;
}

function Editor({ country }: { country?: AdminCountry }) {
  const [, go] = useLocation();
  const [code, setCode] = useState("");
  const [title, setTitle] = useState(fullI18n(country?.title));
  const exit = useExit("/admin/catalog/countries");

  const valid = title.ru.trim() !== "" && (country !== undefined || /^[a-z]{2}$/.test(code));
  const act = useSave(valid ? t("save") : null, async () => {
    if (country) await send("PATCH", `/admin/countries/${country.code}`, { title: compact(title) });
    else await send("POST", "/admin/countries", { code, title: compact(title) });
    exit();
  });
  const remove = () =>
    act(async () => {
      if (!country || !(await confirm(t("country.deleteConfirm", { title: pick(country.title) })))) return false;
      await send("DELETE", `/admin/countries/${country.code}`);
      go("/admin/catalog/countries", { replace: true });
    });

  return (
    <div className="screen">
      <div className="headline">
        <h1>{country ? `${flag(country.code)} ${pick(country.title)}` : t("country.new")}</h1>
        {country && <p>{country.code.toUpperCase()}</p>}
      </div>
      <Section footer={country ? undefined : t("country.codeNote")}>
        {!country && (
          <Field label={t("country.code")} invalid={code !== "" && code.length !== 2}>
            <input
              value={code}
              maxLength={2}
              autoCapitalize="none"
              onChange={(e) => setCode(e.target.value.toLowerCase().replace(/[^a-z]/g, ""))}
            />
          </Field>
        )}
        <I18nFields label={t("country.title")} value={title} invalid={!title.ru.trim()} onChange={setTitle} />
      </Section>
      {country && (
        <Section footer={t("country.deleteNote")}>
          <Row title={t("country.delete")} tone="bad" onClick={remove} />
        </Section>
      )}
    </div>
  );
}
