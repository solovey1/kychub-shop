import { useState } from "react";
import { useLocation } from "wouter";
import { report, useBusy } from "../../action";
import { ApiError, send, useFetch, type Ticket } from "../../api";
import { alert, confirm, success, useMainButton } from "../../telegram";
import { t } from "../../i18n";
import { Chat } from "../../ui/Chat";
import { TicketOrder } from "./TicketOrder";

export function TicketChat({ tid, cid, admin }: { tid: number; cid: number; admin: boolean }) {
  const [, go] = useLocation();
  const [version, setVersion] = useState(0);
  const { data: ticket, reload } = useFetch<Ticket>(`/tickets/${tid}`, ["ticket"]);
  const { busy, run } = useBusy();

  const take = () =>
    run(async () => {
      try {
        await send("POST", `/tickets/${tid}/take`);
        success();
        setVersion((v) => v + 1);
        reload();
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
      title={(code) => t("ticket.title", { id: code })}
      onHandover={ticket && ticket.status !== "closed" && (admin || ticket.mine) ? () => go(`/ticket/${tid}/handover`) : undefined}
      onClose={ticket?.mine && ticket.status === "taken" ? close : undefined}
      header={ticket?.order_id ? <TicketOrder id={ticket.order_id} /> : undefined}
    />
  );
}
