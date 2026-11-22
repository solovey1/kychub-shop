import { useLocation } from "wouter";
import { t } from "../i18n";
import { Empty, Row, Section } from "../ui/kit";
import { visibleSections } from "./access";

export function Admin({ roles }: { roles: string[] }) {
  const [, go] = useLocation();
  const sections = visibleSections(roles);
  return (
    <div className="screen">
      <div className="headline">
        <h1>{t("tab.admin")}</h1>
      </div>
      {sections.length === 0 && <Empty text={t("admin.empty")} />}
      {sections.length > 0 && (
        <Section>
          {sections.map((s) => (
            <Row
              key={s.id}
              title={`${s.emoji} ${t(s.titleKey)}`}
              sub={t(s.descKey)}
              chevron
              onClick={() => go(s.path)}
            />
          ))}
        </Section>
      )}
    </div>
  );
}
