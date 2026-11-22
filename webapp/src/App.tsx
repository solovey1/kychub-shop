import { useEffect } from "react";
import { Redirect, Route, Router, Switch, useLocation } from "wouter";
import { useHashLocation } from "wouter/use-hash-location";
import { Admin } from "./admin/Admin";
import { allowed, hasAdminTab } from "./admin/access";
import { AdminOrderScreen, AssignScreen } from "./admin/orders/Order";
import { AdminOrders } from "./admin/orders/Orders";
import { ExecutorScreen, NewExecutor } from "./admin/people/Executor";
import { People } from "./admin/people/People";
import { UserScreen } from "./admin/people/User";
import { Catalog } from "./admin/catalog/Catalog";
import { CategoryForm } from "./admin/catalog/Category";
import { CountryForm } from "./admin/catalog/Country";
import { ProductForm } from "./admin/catalog/Product";
import { ServiceForm } from "./admin/catalog/Service";
import { Stock } from "./admin/catalog/Stock";
import { VariantForm } from "./admin/catalog/Variant";
import { useExpired, useFetch, type Me } from "./api";
import { setLang, t } from "./i18n";
import { startLive } from "./live";
import { canGoBack, parentOf } from "./nav";
import { Balance } from "./screens/buyer/Balance";
import { OrderScreen } from "./screens/buyer/Order";
import { Orders } from "./screens/buyer/Orders";
import { ExecOrder } from "./screens/executor/ExecOrder";
import { Offer } from "./screens/executor/Offer";
import { Work, type WorkSeg } from "./screens/executor/Work";
import { Handover } from "./screens/staff/Handover";
import { ReviewOrder } from "./screens/staff/ReviewOrder";
import { Support, type SupportSeg } from "./screens/staff/Support";
import { TicketChat } from "./screens/staff/TicketChat";
import { initData, startTelegram, tg, useBackButton, useKeyboard } from "./telegram";
import { Chat } from "./ui/Chat";
import { Failure, Hint, Loading } from "./ui/kit";
import { Tabs } from "./ui/Tabs";
import { useUnreadFeed } from "./unread";

const LINK = /^\/(chat|ticket|orders)\/[0-9/]+$/;
const TOP = /^\/(orders|balance|admin|work\/(queue|mine|wallet)|support\/(tickets|review))$/;

function Shell({ me }: { me: Me }) {
  const [path, go] = useLocation();
  const top = TOP.test(path);
  const keyboard = useKeyboard();
  // nothing before this screen (opened by a bot button): back leads to its parent, not out of the app
  useBackButton(!top, () => (canGoBack() ? history.back() : go(parentOf(path), { replace: true })));
  useEffect(startLive, []);
  useUnreadFeed();
  useEffect(() => {
    // a bot button opens the app as /app/?to=/chat/5: go there once and drop the parameter
    const to = new URLSearchParams(location.search).get("to");
    if (to === null) return;
    if (LINK.test(to)) go(to, { replace: true });
    history.replaceState(null, "", location.pathname + location.hash);
  }, []);

  const tabs = [
    { to: "/orders", key: "orders" },
    { to: "/balance", key: "balance" },
    ...(me.roles.includes("executor") ? [{ to: "/work/queue", key: "work" }] : []),
    ...(me.roles.some((r) => r === "manager" || r === "admin")
      ? [{ to: "/support/tickets", key: "support" }]
      : []),
    ...(hasAdminTab(me.roles) ? [{ to: "/admin", key: "admin" }] : []),
  ];
  const id = (p: { id?: string }) => Number(p.id);
  const staff = hasAdminTab(me.roles);
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
        <Route path="/ticket/:id/handover">{(p) => <Handover tid={id(p)} me={me.id} />}</Route>
        <Route path="/ticket/:id/:cid">
          {(p) => <TicketChat tid={id(p)} cid={Number(p.cid)} admin={allowed(me.roles, "admin")} />}
        </Route>
        {staff && (
          <>
            <Route path="/admin">
              <Admin roles={me.roles} />
            </Route>
            <Route path="/admin/people">
              <People seg="users" roles={me.roles} />
            </Route>
            <Route path="/admin/people/executors">
              <People seg="executors" roles={me.roles} />
            </Route>
            <Route path="/admin/people/managers">
              <People seg="managers" roles={me.roles} />
            </Route>
            <Route path="/admin/people/u/:id">{(p) => <UserScreen id={id(p)} viewer={me.roles} />}</Route>
            <Route path="/admin/people/e/new">
              <NewExecutor />
            </Route>
            <Route path="/admin/people/e/:id">{(p) => <ExecutorScreen id={id(p)} />}</Route>
            <Route path="/admin/orders">
              <AdminOrders />
            </Route>
            <Route path="/admin/orders/:id/assign">{(p) => <AssignScreen id={id(p)} />}</Route>
            <Route path="/admin/orders/:id">{(p) => <AdminOrderScreen id={id(p)} viewer={me.roles} />}</Route>
            <Route path="/admin/catalog">
              <Catalog seg="catalog" />
            </Route>
            <Route path="/admin/catalog/services">
              <Catalog seg="services" />
            </Route>
            <Route path="/admin/catalog/countries">
              <Catalog seg="countries" />
            </Route>
            <Route path="/admin/catalog/c/new/in/:parent">
              {(p) => <CategoryForm id={null} parent={Number(p.parent) || null} />}
            </Route>
            <Route path="/admin/catalog/c/:id/edit">{(p) => <CategoryForm id={id(p)} parent={null} />}</Route>
            <Route path="/admin/catalog/c/:id">{(p) => <Catalog seg="catalog" cat={id(p)} />}</Route>
            <Route path="/admin/catalog/p/new/in/:cat">
              {(p) => <ProductForm id={null} category={Number(p.cat)} />}
            </Route>
            <Route path="/admin/catalog/p/:pid/v/new">
              {(p) => <VariantForm pid={Number(p.pid)} id={null} />}
            </Route>
            <Route path="/admin/catalog/p/:pid/v/:id/stock">
              {(p) => <Stock pid={Number(p.pid)} id={id(p)} />}
            </Route>
            <Route path="/admin/catalog/p/:pid/v/:id">
              {(p) => <VariantForm pid={Number(p.pid)} id={id(p)} />}
            </Route>
            <Route path="/admin/catalog/p/:id">{(p) => <ProductForm id={id(p)} category={0} />}</Route>
            <Route path="/admin/catalog/s/new">
              <ServiceForm id={null} />
            </Route>
            <Route path="/admin/catalog/s/:id">{(p) => <ServiceForm id={id(p)} />}</Route>
            <Route path="/admin/catalog/k/new">
              <CountryForm code={null} />
            </Route>
            <Route path="/admin/catalog/k/:code">{(p) => <CountryForm code={p.code ?? null} />}</Route>
          </>
        )}
        <Route>
          <Redirect to="/orders" replace />
        </Route>
      </Switch>
      {!keyboard && <Tabs tabs={tabs} />}
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
