import { useState } from "react";
import { useLocation } from "wouter";
import { report, useBusy } from "../../action";
import { ApiError, send, useFetch, type Ticket } from "../../api";
import { alert, confirm, success, useMainButton } from "../../telegram";
import { t } from "../../i18n";
import { Chat } from "../../ui/Chat";

export function TicketChat({ tid, cid }: { tid: number; cid: number }) {
  const [, go] = useLocation();
  const [version, setVersion] = useState(0);
  const open = useFetch<Ticket[]>("/tickets?scope=open", ["ticket"]);
  const mine = useFetch<Ticket[]>("/tickets?scope=mine", ["ticket"]);
  const { busy, run } = useBusy();
  const ticket = [...(mine.data ?? []), ...(open.data ?? [])].find((x) => x.id === tid);

  const take = () =>
    run(async () => {
      try {
        await send("POST", `/tickets/${tid}/take`);
        success();
        setVersion((v) => v + 1);
        open.reload();
        mine.reload();
      } catch (e) {
        if (e instanceof ApiError && e.status === 409) {
          await alert(t("ticket.gone"));
          go("/support/tickets", { replace: true });
        } else await report(e);
      }
    });
  const close = () =>
    run(async () => {
      if (!(await confirm(t("ticket.closeConfirm")))) return;
      try {
        await send("POST", `/tickets/${tid}/close`);
        success();
        go("/support/tickets", { replace: true });
      } catch (e) {
        await report(e);
      }
    });
  useMainButton(ticket && !ticket.mine && ticket.status === "open" ? t("ticket.take") : null, take, { busy });

  return (
    <Chat
      cid={cid}
      version={version}
      title={t("ticket.title", { id: tid })}
      onClose={ticket?.mine && ticket.status === "taken" ? close : undefined}
    />
  );
}
