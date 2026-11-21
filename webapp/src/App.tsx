import { useEffect } from "react";
import { Redirect, Route, Router, Switch, useLocation } from "wouter";
import { useHashLocation } from "wouter/use-hash-location";
import { useExpired, useFetch, type Me } from "./api";
import { setLang, t } from "./i18n";
import { startLive } from "./live";
import { Balance } from "./screens/buyer/Balance";
import { OrderScreen } from "./screens/buyer/Order";
import { Orders } from "./screens/buyer/Orders";
import { ExecOrder } from "./screens/executor/ExecOrder";
import { Offer } from "./screens/executor/Offer";
import { Work, type WorkSeg } from "./screens/executor/Work";
import { ReviewOrder } from "./screens/staff/ReviewOrder";
import { Support, type SupportSeg } from "./screens/staff/Support";
import { TicketChat } from "./screens/staff/TicketChat";
import { initData, startTelegram, tg, useBackButton } from "./telegram";
import { Chat } from "./ui/Chat";
import { Failure, Hint, Loading } from "./ui/kit";
import { Tabs } from "./ui/Tabs";

const TOP = /^\/(orders|balance|work\/(queue|mine|wallet)|support\/(tickets|review))$/;

function Shell({ me }: { me: Me }) {
  const [path] = useLocation();
  const top = TOP.test(path);
  useBackButton(!top, () => history.back());
  useEffect(startLive, []);

  const tabs = [
    { to: "/orders", key: "orders" },
    { to: "/balance", key: "balance" },
    ...(me.roles.includes("executor") ? [{ to: "/work/queue", key: "work" }] : []),
    ...(me.roles.some((r) => r === "manager" || r === "admin")
      ? [{ to: "/support/tickets", key: "support" }]
      : []),
  ];
  const id = (p: { id?: string }) => Number(p.id);
  return (
    <div className="app">
      <Switch>
        <Route path="/orders" component={Orders} />
        <Route path="/orders/:id/chat/:cid">
          {(p) => <Chat cid={Number(p.cid)} title={t("chat.order", { id: p.id })} />}
        </Route>
        <Route path="/orders/:id">{(p) => <OrderScreen id={id(p)} />}</Route>
        <Route path="/balance" component={Balance} />
        <Route path="/chat/:cid">{(p) => <Chat cid={Number(p.cid)} title={t("support.title")} />}</Route>
        <Route path="/work/offer/:id">{(p) => <Offer id={id(p)} />}</Route>
        <Route path="/work/order/:id/chat/:cid">
          {(p) => <Chat cid={Number(p.cid)} title={t("chat.order", { id: p.id })} />}
        </Route>
        <Route path="/work/order/:id">{(p) => <ExecOrder id={id(p)} />}</Route>
        <Route path="/work/:seg">{(p) => <Work seg={p.seg as WorkSeg} />}</Route>
        <Route path="/support/review/:id">{(p) => <ReviewOrder id={id(p)} />}</Route>
        <Route path="/support/:seg">
          {(p) => <Support seg={p.seg as SupportSeg} admin={me.roles.includes("admin")} />}
        </Route>
        <Route path="/ticket/:id/:cid">
          {(p) => <TicketChat tid={id(p)} cid={Number(p.cid)} />}
        </Route>
        <Route>
          <Redirect to="/orders" replace />
        </Route>
      </Switch>
      {top && <Tabs tabs={tabs} />}
    </div>
  );
}

export default function App() {
  const expired = useExpired();
  const { data: me, error, reload } = useFetch<Me>(initData ? "/me" : null);
  useEffect(startTelegram, []);
  setLang(me?.language ?? tg?.initDataUnsafe.user?.language_code);

  if (!initData) return <Hint title={t("gate.title")} text={t("gate.text")} />;
  if (expired) return <Hint title={t("expired.title")} text={t("expired.text")} action />;
  if (error && !me) return <Failure error={error} retry={reload} />;
  if (!me) return <Loading />;
  return (
    <Router hook={useHashLocation}>
      <Shell me={me} />
    </Router>
  );
}
