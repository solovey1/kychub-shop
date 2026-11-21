// Dev only (see main.tsx): a fake Telegram WebApp and a fake API, so every screen can be seen in a
// plain browser. ?roles=executor,manager,admin (default: all, empty: a plain buyer), ?lang=ru|en|uk.
// The theme follows prefers-color-scheme. Nothing here reaches a production build.

const query = new URLSearchParams(location.search);
const roles = (query.get("roles") ?? "executor,manager,admin").split(",").filter(Boolean);
const dark = matchMedia("(prefers-color-scheme: dark)").matches;

const theme = dark
  ? {
      bg_color: "#17212b",
      text_color: "#f5f5f5",
      hint_color: "#708499",
      button_color: "#5288c1",
      button_text_color: "#ffffff",
      secondary_bg_color: "#232e3c",
      destructive_text_color: "#ec3942",
      section_separator_color: "#0d1621",
    }
  : {
      bg_color: "#ffffff",
      text_color: "#000000",
      hint_color: "#8a8a8e",
      button_color: "#2481cc",
      button_text_color: "#ffffff",
      secondary_bg_color: "#f1f1f4",
      destructive_text_color: "#e53935",
      section_separator_color: "#d9d9de",
    };
for (const [k, v] of Object.entries(theme))
  document.documentElement.style.setProperty(`--tg-theme-${k.replaceAll("_", "-")}`, v);

// native buttons as DOM
const native = document.getElementById("native")!;
const mainEl = document.createElement("button");
mainEl.className = "mock-main";
mainEl.hidden = true;
native.append(mainEl);
const backEl = document.createElement("button");
backEl.className = "mock-back";
backEl.hidden = true;
backEl.textContent = "Назад";
document.body.prepend(backEl);

const button = (el: HTMLElement) => ({
  show: () => (el.hidden = false),
  hide: () => (el.hidden = true),
  onClick: (cb: () => void) => el.addEventListener("click", cb),
  offClick: (cb: () => void) => el.removeEventListener("click", cb),
});

window.Telegram = {
  WebApp: {
    initData: "mock",
    initDataUnsafe: { user: { id: 1, language_code: query.get("lang") ?? "ru" } },
    themeParams: theme,
    colorScheme: dark ? "dark" : "light",
    MainButton: {
      ...button(mainEl),
      setText: (text) => (mainEl.textContent = text),
      setParams: (p) => {
        if (p.color) mainEl.style.background = p.color;
      },
      showProgress: () => (mainEl.style.opacity = "0.6"),
      hideProgress: () => (mainEl.style.opacity = ""),
    },
    BackButton: button(backEl),
    HapticFeedback: { notificationOccurred: () => {} },
    ready: () => {},
    expand: () => {},
    close: () => console.info("WebApp.close()"),
    setHeaderColor: () => {},
    showConfirm: (message, cb) => (console.info("confirm:", message), cb(true)),
    showAlert: (message, cb) => (console.info("alert:", message), cb?.()),
  },
};
backEl.addEventListener("click", () => history.back());

// fake API
const minutes = (n: number) => new Date(Date.now() + n * 60_000).toISOString();
const ago = (n: number) => minutes(-n);

type Brief = {
  id: number;
  status: string;
  product: string;
  variant: string;
  country: string | null;
  total: string;
  created_at: string;
};
const orders: (Brief & { alias: string | null; result: string | null; cancel?: boolean })[] = [
  { id: 1042, status: "assigned", product: "Аккаунт Instagram, прогретый", variant: "30 дней", country: "us", total: "12.50", created_at: ago(35), alias: "Орион", result: null },
  { id: 1041, status: "in_queue", product: "Аккаунт Instagram, прогретый", variant: "7 дней", country: "de", total: "8.00", created_at: ago(12), alias: null, result: null, cancel: true },
  { id: 1038, status: "ready", product: "Регистрация Google Ads", variant: "С верификацией", country: null, total: "45.00", created_at: ago(300), alias: "Фокс", result: null },
  { id: 1030, status: "completed", product: "Прокси, 10 штук", variant: "Residential", country: "pl", total: "20.00", created_at: ago(2000), alias: "Фокс", result: "http://user1:pass1@10.0.0.1:8080\nhttp://user2:pass2@10.0.0.2:8080" },
  { id: 1027, status: "completed", product: "Ключ активации", variant: "Pro, 1 год", country: null, total: "6.00", created_at: ago(4000), alias: null, result: "XK4T-9PLM-27QA-RW88" },
  { id: 1020, status: "cancelled", product: "Аккаунт Facebook", variant: "Старый, 2019", country: "ua", total: "15.00", created_at: ago(6000), alias: null, result: null },
  { id: 1011, status: "refunded", product: "Регистрация Google Ads", variant: "Базовая", country: null, total: "30.00", created_at: ago(9000), alias: "Орион", result: null },
  { id: 1005, status: "failed", product: "Прокси, 10 штук", variant: "Mobile", country: "us", total: "40.00", created_at: ago(12000), alias: "Фокс", result: null },
];

const entry = (id: number, kind: string, amount: string, after: string, order_id: number | null, m: number) => ({
  id,
  kind,
  amount,
  balance_after: after,
  order_id,
  created_at: ago(m),
});

const SVG =
  '<svg xmlns="http://www.w3.org/2000/svg" width="480" height="320"><rect width="480" height="320" fill="#26a17b"/><rect x="40" y="48" width="400" height="36" rx="8" fill="#ffffff" opacity=".9"/><rect x="40" y="108" width="280" height="24" rx="8" fill="#ffffff" opacity=".6"/><rect x="40" y="152" width="340" height="24" rx="8" fill="#ffffff" opacity=".6"/><rect x="40" y="236" width="140" height="44" rx="10" fill="#ffffff"/></svg>';

type Msg = { id: number; sender_role: string; mine: boolean; text: string | null; media_type: string | null; created_at: string };
const msg = (id: number, sender_role: string, mine: boolean, text: string | null, m: number, media_type: string | null = null): Msg => ({
  id, sender_role, mine, text, media_type, created_at: ago(m),
});
const chats: Record<number, { items: Msg[]; can_post: boolean }> = {
  1: {
    can_post: true,
    items: [
      msg(1, "executor", false, "Здравствуйте! Начинаю работу, закончу в течение часа.", 90),
      msg(2, "buyer", true, "Отлично, жду.", 88),
      msg(3, "executor", false, "Готово, проверьте скриншот.", 30, "photo"),
      msg(4, "executor", false, "Если нужна другая страна, напишите.", 29),
      msg(5, "buyer", true, "Спасибо, всё подходит.", 5),
    ],
  },
  2: { can_post: true, items: [msg(10, "buyer", true, "Здравствуйте, не пришёл результат по заказу.", 60), msg(11, "manager", false, "Добрый день, уже смотрим.", 50)] },
  3: { can_post: true, items: [msg(20, "buyer", false, "Не могу найти файл с результатом.", 25), msg(21, "manager", true, "Файлы пришлёт бот в личном чате, проверьте его.", 20)] },
  4: { can_post: false, items: [msg(30, "buyer", false, "Вопрос по возврату.", 400), msg(31, "manager", true, "Возврат выполнен.", 380)] },
};

const queue = [
  { id: 1051, status: "in_queue", product: "Аккаунт Instagram, прогретый", country: "us", earning: "4.00", deadline_minutes: 90 },
  { id: 1052, status: "in_queue", product: "Регистрация Google Ads", country: null, earning: "11.50", deadline_minutes: 180 },
  { id: 1053, status: "in_queue", product: "Прокси, 10 штук", country: "pl", earning: "2.20", deadline_minutes: 60 },
];
const execOrders = [
  { id: 1042, status: "assigned", product: "Аккаунт Instagram, прогретый", variant: "30 дней", country: "us", deadline_at: minutes(52) },
  { id: 1038, status: "ready", product: "Регистрация Google Ads", variant: "С верификацией", country: null, deadline_at: minutes(-20) },
  { id: 1030, status: "completed", product: "Прокси, 10 штук", variant: "Residential", country: "pl", deadline_at: null },
];
const form = [
  { key: "login", label: "Логин", type: "text", required: true, options: null, max_length: 64 },
  { key: "password", label: "Пароль", type: "text", required: true, options: null, max_length: 64 },
  { key: "plan", label: "Тариф", type: "select", required: false, options: ["Базовый", "Расширенный"], max_length: 64 },
  { key: "note", label: "Комментарий", type: "textarea", required: false, options: null, max_length: 500 },
];
const execDetail = (id: number) => {
  const o = execOrders.find((x) => x.id === id) ?? execOrders[0];
  return {
    id: o.id,
    status: o.status,
    product: o.product,
    country: o.country,
    earning: "4.00",
    deadline_minutes: 90,
    deadline_at: o.deadline_at,
    fields: [
      { label: "Страна", value: "США", is_file: false },
      { label: "Почта для регистрации", value: "buyer.mail@example.com", is_file: false },
      { label: "Скриншот профиля", value: null, is_file: true },
    ],
    result_form: o.status === "assigned" ? form : null,
    result: o.status === "assigned" ? null : { login: "farm_account_01", password: "••••••••" },
  };
};

const tickets = [
  { id: 71, status: "open", order_id: 1042, buyer_name: "Андрей К.", mine: false, conversation_id: 3, created_at: ago(14) },
  { id: 70, status: "open", order_id: null, buyer_name: "Maria", mine: false, conversation_id: 3, created_at: ago(95) },
  { id: 68, status: "taken", order_id: 1030, buyer_name: "Игорь", mine: true, conversation_id: 3, created_at: ago(300) },
  { id: 60, status: "closed", order_id: 1011, buyer_name: "Олег", mine: true, conversation_id: 4, created_at: ago(900) },
];

function brief(o: Brief) {
  return { id: o.id, status: o.status, product: o.product, variant: o.variant, country: o.country, total: o.total, created_at: o.created_at };
}

function route(method: string, url: URL, body: unknown): unknown {
  const path = url.pathname.replace(/^\/api/, "");
  const q = url.searchParams;
  let m: RegExpMatchArray | null;
  if (path === "/me")
    return {
      id: 1,
      name: "Сергей",
      language: query.get("lang") ?? "ru",
      roles,
      balance: "128.40",
      executor: roles.includes("executor") ? { hold: "12.40", available: "58.75" } : null,
    };
  if (path === "/orders") return { items: orders.map(brief), total: orders.length, page: 0, page_size: 20 };
  if ((m = path.match(/^\/orders\/(\d+)$/))) {
    const o = orders.find((x) => x.id === Number(m![1]));
    if (!o) throw 404;
    const done = o.status === "completed";
    return { ...brief(o), executor_alias: o.alias, result: done ? o.result : null, result_files: o.id === 1030 ? 2 : 0, can_cancel: !!o.cancel };
  }
  if ((m = path.match(/^\/orders\/(\d+)\/cancel$/))) {
    const o = orders.find((x) => x.id === Number(m![1]));
    if (o) (o.status = "cancelled"), (o.cancel = false);
    return { order_id: Number(m[1]), refunded: o?.total ?? "0.00" };
  }
  if (path === "/balance")
    return {
      balance: "128.40",
      entries: [
        entry(5, "purchase", "-12.50", "128.40", 1042, 35),
        entry(4, "topup", "100.00", "140.90", null, 700),
        entry(3, "refund", "30.00", "40.90", 1011, 8000),
        entry(2, "promo_bonus", "2.50", "10.90", null, 9000),
        entry(1, "purchase", "-6.00", "8.40", 1027, 4000),
      ],
    };
  if (path === "/support") return { ticket_id: 72, conversation_id: 2, created: true };
  if (path.match(/^\/orders\/\d+\/chat$/)) return { conversation_id: 1, can_post: true };
  if ((m = path.match(/^\/conversations\/(\d+)\/messages$/))) {
    const c = chats[Number(m[1])] ?? chats[2];
    if (method === "POST") {
      const sent = msg(Date.now() % 100000, "buyer", true, (body as { text: string }).text, 0);
      c.items.push(sent);
      return sent;
    }
    return { items: c.items, has_more: false, can_post: c.can_post };
  }
  if (path.match(/^\/files\//)) return new Blob([SVG], { type: "image/svg+xml" });

  if (path === "/executor/queue") return queue;
  if ((m = path.match(/^\/executor\/orders\/(\d+)\/take$/))) return execDetail(Number(m[1]));
  if (path === "/executor/orders") return { items: execOrders, total: execOrders.length, page: 0, page_size: 20 };
  if ((m = path.match(/^\/executor\/orders\/(\d+)\/(refuse|result)$/))) return m[2] === "refuse" ? { ok: true } : execDetail(Number(m[1]));
  if ((m = path.match(/^\/executor\/orders\/(\d+)$/))) return execDetail(Number(m[1]));
  if (path === "/executor/stats") return { completed: 41, failed: 1, overdue: 2, refused: 3, avg_minutes: 54.4, avg_score: 4.8 };
  if (path === "/executor/balance" || path === "/executor/wallet")
    return {
      hold: "12.40",
      available: "58.75",
      wallet: "TQrZ9sT3xJ4kLw8vUe2Yb7NcMdHfPa6GhV",
      minimum: "10.00",
      entries: [
        entry(9, "executor_earning", "4.00", "58.75", 1042, 40),
        entry(8, "hold_release", "6.50", "54.75", 1030, 600),
        entry(7, "withdrawal", "-25.00", "48.25", null, 3000),
      ],
    };
  if (path === "/executor/withdraw") return { id: 5, amount: "58.75", address: "TQrZ" };

  if (path === "/tickets") {
    const scope = q.get("scope");
    return tickets.filter((t) => (scope === "open" ? t.status === "open" : scope === "mine" ? t.mine : true));
  }
  if (path.match(/^\/tickets\/\d+\/(take|close)$/)) return path.endsWith("take") ? { conversation_id: 3 } : { ok: true };
  if (path === "/staff/orders") return orders.filter((o) => o.status === "ready").map((o) => ({ ...brief(o), executor_id: 7, ready_at: ago(25) }));
  if ((m = path.match(/^\/staff\/orders\/(\d+)$/))) {
    const o = orders.find((x) => x.id === Number(m![1])) ?? orders[2];
    return {
      ...brief(o),
      executor_id: 7,
      ready_at: ago(25),
      earning: "11.50",
      fields: [
        { label: "Почта для регистрации", value: "buyer.mail@example.com", is_file: false },
        { label: "Рекламный бюджет", value: "500 USD", is_file: false },
        { label: "Паспорт", value: null, is_file: true },
      ],
      result: "Аккаунт: ads-4471@example.com\nПароль: Zt9!kLm2\nКлиентский ID: 482-119-7765",
      result_files: 1,
    };
  }
  if (path.match(/^\/staff\/orders\/\d+\/(confirm|send_back)$/)) return { ok: true };
  if ((m = path.match(/^\/staff\/orders\/(\d+)\/fail$/))) return { order_id: Number(m[1]), refunded: "45.00" };
  throw 404;
}

const real = window.fetch.bind(window);
window.fetch = async (input, init) => {
  const url = new URL(typeof input === "string" ? input : input instanceof URL ? input.href : input.url, location.href);
  if (!url.pathname.startsWith("/api/")) return real(input, init);
  await new Promise((r) => setTimeout(r, 120));
  try {
    const data = route(init?.method ?? "GET", url, init?.body ? JSON.parse(String(init.body)) : undefined);
    return data instanceof Blob ? new Response(data) : Response.json(data);
  } catch (e) {
    if (typeof e === "number") return Response.json({ detail: "Not found" }, { status: e });
    throw e;
  }
};

export {};
