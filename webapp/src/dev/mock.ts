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
    viewportHeight: innerHeight,
    viewportStableHeight: innerHeight,
    onEvent: () => {},
    offEvent: () => {},
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
  unread?: number;
};
const orders: (Brief & { alias: string | null; result: string | null; cancel?: boolean })[] = [
  { id: 1042, status: "assigned", product: "Аккаунт Instagram, прогретый", variant: "30 дней", country: "us", total: "12.50", created_at: ago(35), alias: "Орион", result: null, unread: 2 },
  { id: 1041, status: "in_queue", product: "Аккаунт Instagram, прогретый", variant: "7 дней", country: "de", total: "8.00", created_at: ago(12), alias: null, result: null, cancel: true },
  { id: 1038, status: "ready", product: "Регистрация Google Ads", variant: "С верификацией", country: null, total: "45.00", created_at: ago(300), alias: "Фокс", result: null, unread: 120 },
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
  { id: 1042, status: "assigned", product: "Аккаунт Instagram, прогретый", variant: "30 дней", country: "us", deadline_at: minutes(52), unread: 3 },
  { id: 1038, status: "ready", product: "Регистрация Google Ads", variant: "С верификацией", country: null, deadline_at: minutes(-20), unread: 0 },
  { id: 1030, status: "completed", product: "Прокси, 10 штук", variant: "Residential", country: "pl", deadline_at: null, unread: 0 },
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
    extension: o.status === "assigned" ? { pending_minutes: null, can_request: true, options: [15, 30, 60, 120, 360, 1440] } : null,
    result_form: o.status === "assigned" ? form : null,
    result: o.status === "assigned" ? null : { login: "farm_account_01", password: "••••••••" },
  };
};

const tickets = [
  { id: 71, status: "open", order_id: 1042, buyer_name: "Андрей К.", mine: false, conversation_id: 3, created_at: ago(14), unread: 1 },
  { id: 70, status: "open", order_id: null, buyer_name: "Maria", mine: false, conversation_id: 3, created_at: ago(95), unread: 0 },
  { id: 68, status: "taken", order_id: 1030, buyer_name: "Игорь", mine: true, conversation_id: 3, created_at: ago(300), unread: 4 },
  { id: 60, status: "closed", order_id: 1011, buyer_name: "Олег", mine: true, conversation_id: 4, created_at: ago(900), unread: 0 },
];

function brief(o: Brief) {
  return { id: o.id, status: o.status, product: o.product, variant: o.variant, country: o.country, total: o.total, created_at: o.created_at, unread: o.unread ?? 0 };
}

// --- admin: the catalog, stateful in memory so every screen can be clicked through
type I18n = Record<string, string>;
const tr = (ru: string, en: string, uk = ru): I18n => ({ ru, en, uk });
/** A failed request with the JSON body the real API sends: 409 {code, detail}, 422 {code, detail, field}. */
type Fail = { status: number; body: { code?: string; detail: string; field?: string } };
const fail = (status: number, code: string, detail: string, field?: string): Fail => ({
  status,
  body: { code, detail, field },
});

type MCategory = { id: number; parent_id: number | null; title: I18n; position: number; is_active: boolean };
type MVariant = { id: number; country_code: string | null; title: I18n | null; price: string; is_active: boolean };
type MProduct = {
  id: number;
  category_id: number;
  service_id: number | null;
  title: I18n;
  description: I18n;
  input_schema: { fields: object[] };
  result_schema: { fields: object[] };
  fulfillment_type: string;
  fulfillment_config: { text?: string };
  is_active: boolean;
  variants: MVariant[];
  used: string | null;
};
type MService = {
  id: number;
  code: string;
  title: string;
  deadline_minutes: number;
  assign_mode: string;
  executor_percent: number;
  is_active: boolean;
};
type MCountry = { code: string; title: I18n };
type MStock = { units: { id: number; payload: string }[]; unlimited: string | null };

const mCategories: MCategory[] = [
  { id: 1, parent_id: null, title: tr("Аккаунты", "Accounts", "Акаунти"), position: 0, is_active: true },
  { id: 2, parent_id: null, title: tr("Прокси", "Proxies", "Проксі"), position: 1, is_active: true },
  { id: 3, parent_id: null, title: tr("Услуги", "Services", "Послуги"), position: 2, is_active: true },
  { id: 4, parent_id: 1, title: tr("Instagram", "Instagram"), position: 0, is_active: true },
  { id: 5, parent_id: 1, title: tr("Facebook", "Facebook"), position: 1, is_active: true },
  { id: 6, parent_id: 2, title: tr("Residential", "Residential"), position: 0, is_active: true },
  { id: 7, parent_id: 2, title: tr("Mobile", "Mobile"), position: 1, is_active: false },
  { id: 8, parent_id: 3, title: tr("Регистрации", "Registrations", "Реєстрації"), position: 0, is_active: true },
];
const mProducts: MProduct[] = [
  {
    id: 1,
    category_id: 5,
    service_id: null,
    title: tr("Аккаунт Facebook, старый", "Facebook account, aged", "Акаунт Facebook, старий"),
    description: tr("Аккаунт 2019 года с историей.", "An account from 2019 with history.", "Акаунт 2019 року з історією."),
    input_schema: { fields: [] },
    result_schema: { fields: [] },
    fulfillment_type: "stock",
    fulfillment_config: {},
    is_active: true,
    variants: [
      { id: 1, country_code: "us", title: null, price: "15.00", is_active: true },
      { id: 2, country_code: "de", title: tr("С почтой", "With mailbox", "З поштою"), price: "18.50", is_active: true },
    ],
    used: null,
  },
  {
    id: 2,
    category_id: 4,
    service_id: 1,
    title: tr("Аккаунт Instagram, прогретый", "Instagram account, warmed up", "Акаунт Instagram, прогрітий"),
    description: tr("Прогрев аккаунта под ключ.", "A warmed-up account, ready to use.", "Прогрів акаунта під ключ."),
    input_schema: {
      fields: [
        {
          key: "profile_name",
          type: "text",
          required: true,
          label: tr("Имя профиля", "Profile name", "Ім'я профілю"),
          placeholder: tr("Например, my_shop", "For example, my_shop", "Наприклад, my_shop"),
          max_length: 64,
        },
        {
          key: "niche",
          type: "choice",
          required: false,
          label: tr("Тематика", "Niche", "Тематика"),
          hint: tr("Выберите одну", "Pick one", "Виберіть одну"),
          options: ["Красота", "Фитнес", "Еда"],
        },
        {
          key: "email",
          type: "email",
          required: true,
          label: tr("Почта покупателя", "Buyer email", "Пошта покупця"),
          hidden_from_executor: true,
        },
      ],
    },
    result_schema: {
      fields: [
        { key: "login", type: "login", required: true, label: tr("Логин", "Login", "Логін") },
        { key: "password", type: "text", required: true, label: tr("Пароль", "Password", "Пароль") },
      ],
    },
    fulfillment_type: "executor",
    fulfillment_config: {},
    is_active: true,
    variants: [
      { id: 3, country_code: "us", title: tr("30 дней", "30 days", "30 днів"), price: "12.50", is_active: true },
      { id: 4, country_code: "pl", title: tr("7 дней", "7 days", "7 днів"), price: "8.00", is_active: false },
    ],
    used: "has_orders",
  },
  {
    id: 3,
    category_id: 4,
    service_id: null,
    title: tr("Гайд по прогреву", "Warm-up guide", "Гайд із прогріву"),
    description: tr("", "", ""),
    input_schema: { fields: [] },
    result_schema: { fields: [] },
    fulfillment_type: "fixed",
    fulfillment_config: { text: "Шаг 1. Заполните профиль.\nШаг 2. Подпишитесь на 20 аккаунтов." },
    is_active: true,
    variants: [{ id: 5, country_code: null, title: null, price: "3.00", is_active: true }],
    used: "has_promo",
  },
  {
    id: 4,
    category_id: 6,
    service_id: null,
    title: tr("Прокси, 10 штук", "Proxies, 10 pcs", "Проксі, 10 штук"),
    description: tr("Резидентские прокси, выдаются вручную.", "Residential proxies, issued by hand.", "Резидентські проксі, видаються вручну."),
    input_schema: { fields: [] },
    result_schema: { fields: [] },
    fulfillment_type: "manual",
    fulfillment_config: {},
    is_active: true,
    variants: [{ id: 6, country_code: "pl", title: null, price: "20.00", is_active: true }],
    used: null,
  },
  {
    id: 5,
    category_id: 7,
    service_id: null,
    title: tr("Mobile прокси, сутки", "Mobile proxy, one day", "Mobile проксі, доба"),
    description: tr("", "", ""),
    input_schema: { fields: [] },
    result_schema: { fields: [] },
    fulfillment_type: "stock",
    fulfillment_config: {},
    is_active: false,
    variants: [{ id: 7, country_code: "us", title: null, price: "40.00", is_active: true }],
    used: null,
  },
  {
    id: 6,
    category_id: 8,
    service_id: 2,
    title: tr("Регистрация Google Ads", "Google Ads registration", "Реєстрація Google Ads"),
    description: tr("Регистрация с верификацией.", "Registration with verification.", "Реєстрація з верифікацією."),
    input_schema: {
      fields: [{ key: "email", type: "email", required: true, label: tr("Почта", "Email", "Пошта") }],
    },
    result_schema: {
      fields: [{ key: "account", type: "text", required: true, label: tr("Аккаунт", "Account", "Акаунт") }],
    },
    fulfillment_type: "executor",
    fulfillment_config: {},
    is_active: true,
    variants: [{ id: 8, country_code: null, title: tr("С верификацией", "Verified", "З верифікацією"), price: "45.00", is_active: true }],
    used: "has_orders",
  },
];
const mServices: MService[] = [
  { id: 1, code: "socials", title: "Соцсети", deadline_minutes: 90, assign_mode: "queue", executor_percent: 40, is_active: true },
  { id: 2, code: "ads", title: "Реклама", deadline_minutes: 180, assign_mode: "auto", executor_percent: 35, is_active: true },
];
const mCountries: MCountry[] = [
  { code: "us", title: tr("США", "United States", "США") },
  { code: "de", title: tr("Германия", "Germany", "Німеччина") },
  { code: "pl", title: tr("Польша", "Poland", "Польща") },
];

let nextId = 100;
const mStock = new Map<number, MStock>();
const unit = (payload: string) => ({ id: nextId++, payload });
mStock.set(1, { units: Array.from({ length: 30 }, (_, i) => unit(`fb_user_${1000 + i}:Zq${7000 + i * 13}!`)), unlimited: null });
mStock.set(2, { units: Array.from({ length: 4 }, (_, i) => unit(`fb_de_${200 + i}:Kx${i}9!`)), unlimited: "fb_demo:demo-pass" });
mStock.set(7, { units: Array.from({ length: 3 }, (_, i) => unit(`mob_${i}:10.1.1.${i}:8080`)), unlimited: null });

const mProductOf = (id: number) => {
  const p = mProducts.find((x) => x.id === id);
  if (!p) throw 404;
  return p;
};
const descendants = (id: number): number[] =>
  mCategories.filter((c) => c.parent_id === id).flatMap((c) => [c.id, ...descendants(c.id)]);
const price = (v: unknown) => Number(v).toFixed(2);

/** Swap `id` with its neighbour among `siblings` (already in display order) inside `all`. */
function swap<T extends { id: number }>(all: T[], siblings: T[], id: number, direction: unknown) {
  const i = siblings.findIndex((s) => s.id === id);
  const j = direction === "up" ? i - 1 : i + 1;
  if (i < 0 || j < 0 || j >= siblings.length) return;
  const a = all.indexOf(siblings[i]);
  const b = all.indexOf(siblings[j]);
  [all[a], all[b]] = [all[b], all[a]];
}

function adminRoute(method: string, path: string, body: unknown): unknown {
  const b = (body ?? {}) as Record<string, unknown>;
  const ok = { ok: true };
  let m: RegExpMatchArray | null;

  if (path === "/admin/categories") {
    if (method === "POST") {
      const id = nextId++;
      const siblings = mCategories.filter((c) => c.parent_id === (b.parent_id ?? null));
      mCategories.push({
        id,
        parent_id: (b.parent_id as number | null) ?? null,
        title: b.title as I18n,
        position: siblings.length,
        is_active: b.is_active !== false,
      });
      return { id };
    }
    return [...mCategories]
      .sort((x, y) => x.position - y.position)
      .map((c) => ({
        ...c,
        children: mCategories.filter((x) => x.parent_id === c.id).length,
        products: mProducts.filter((p) => p.category_id === c.id).length,
      }));
  }
  if ((m = path.match(/^\/admin\/categories\/(\d+)\/move$/))) {
    const c = mCategories.find((x) => x.id === Number(m![1]));
    if (!c) throw 404;
    const siblings = mCategories.filter((x) => x.parent_id === c.parent_id).sort((x, y) => x.position - y.position);
    const i = siblings.findIndex((x) => x.id === c.id);
    const o = siblings[b.direction === "up" ? i - 1 : i + 1];
    if (o) [c.position, o.position] = [o.position, c.position];
    return ok;
  }
  if ((m = path.match(/^\/admin\/categories\/(\d+)\/products$/)))
    return mProducts
      .filter((p) => p.category_id === Number(m![1]))
      .map((p) => ({
        id: p.id,
        title: p.title,
        is_active: p.is_active,
        fulfillment_type: p.fulfillment_type,
        variants: p.variants.length,
        price_from: p.variants.length ? price(Math.min(...p.variants.map((v) => Number(v.price)))) : null,
      }));
  if ((m = path.match(/^\/admin\/categories\/(\d+)$/))) {
    const id = Number(m[1]);
    const c = mCategories.find((x) => x.id === id);
    if (!c) throw 404;
    if (method === "DELETE") {
      if (mCategories.some((x) => x.parent_id === id)) throw fail(409, "has_children", "category has subcategories");
      if (mProducts.some((p) => p.category_id === id)) throw fail(409, "has_products", "category has products");
      mCategories.splice(mCategories.indexOf(c), 1);
      return ok;
    }
    if ("parent_id" in b && b.parent_id !== null && (b.parent_id === id || descendants(id).includes(b.parent_id as number)))
      throw fail(409, "cycle", "category inside itself");
    Object.assign(c, b);
    return ok;
  }

  if (path === "/admin/products") {
    const id = nextId++;
    mProducts.push({
      description: {},
      input_schema: { fields: [] },
      result_schema: { fields: [] },
      fulfillment_config: {},
      is_active: true,
      service_id: null,
      ...(b as Partial<MProduct>),
      id,
      variants: [],
      used: null,
    } as MProduct);
    return { id };
  }
  if ((m = path.match(/^\/admin\/products\/(\d+)\/move$/))) {
    const p = mProductOf(Number(m[1]));
    swap(mProducts, mProducts.filter((x) => x.category_id === p.category_id), p.id, b.direction);
    return ok;
  }
  if ((m = path.match(/^\/admin\/products\/(\d+)\/variants$/))) {
    const p = mProductOf(Number(m[1]));
    const id = nextId++;
    p.variants.push({ id, country_code: (b.country_code as string | null) ?? null, title: (b.title as I18n | null) ?? null, price: price(b.price), is_active: b.is_active !== false });
    return { id };
  }
  if ((m = path.match(/^\/admin\/products\/(\d+)$/))) {
    const p = mProductOf(Number(m[1]));
    if (method === "GET")
      return { ...p, variants: p.variants.map((v) => ({ ...v, stock: p.fulfillment_type === "stock" ? (mStock.get(v.id)?.units.length ?? 0) : null })) };
    if (method === "DELETE") {
      if (p.used) throw fail(409, p.used, "product is used");
      mProducts.splice(mProducts.indexOf(p), 1);
      return ok;
    }
    for (const key of ["input_schema", "result_schema"] as const) {
      const fields = ((b[key] as MProduct["input_schema"] | undefined)?.fields ?? []) as { key: string; regex?: string }[];
      if (new Set(fields.map((f) => f.key)).size !== fields.length) throw fail(422, "InvalidField", "duplicate field keys", key);
      for (const f of fields)
        try {
          if (f.regex) new RegExp(f.regex);
        } catch {
          throw fail(422, "InvalidField", `bad regex: ${f.regex}`, key);
        }
    }
    Object.assign(p, b);
    return ok;
  }

  if ((m = path.match(/^\/admin\/variants\/(\d+)\/stock\/unlimited$/))) {
    const s = mStock.get(Number(m[1])) ?? { units: [], unlimited: null };
    s.unlimited = (b.text as string | null) || null;
    mStock.set(Number(m[1]), s);
    return ok;
  }
  if ((m = path.match(/^\/admin\/variants\/(\d+)\/stock$/))) {
    const id = Number(m[1]);
    const s = mStock.get(id) ?? { units: [], unlimited: null };
    mStock.set(id, s);
    if (method === "POST") {
      const lines = String(b.text).split("\n").map((l) => l.trim()).filter(Boolean);
      const fresh = [...new Set(lines)].filter((l) => !s.units.some((u) => u.payload === l));
      s.units.push(...fresh.map(unit));
      return { added: fresh.length, duplicates: lines.length - fresh.length };
    }
    return { free: s.units.length, unlimited: s.unlimited, recent: s.units.slice(-50).reverse() };
  }
  if ((m = path.match(/^\/admin\/variants\/(\d+)$/))) {
    const id = Number(m[1]);
    const p = mProducts.find((x) => x.variants.some((v) => v.id === id));
    const v = p?.variants.find((x) => x.id === id);
    if (!p || !v) throw 404;
    if (method === "DELETE") {
      if (p.used === "has_orders") throw fail(409, "has_orders", "variant has orders");
      p.variants.splice(p.variants.indexOf(v), 1);
      return ok;
    }
    Object.assign(v, b, "price" in b ? { price: price(b.price) } : {});
    return ok;
  }
  if ((m = path.match(/^\/admin\/stock\/(\d+)$/))) {
    for (const s of mStock.values()) s.units = s.units.filter((u) => u.id !== Number(m![1]));
    return ok;
  }

  if (path === "/admin/services") {
    if (method === "GET") return mServices;
    if (mServices.some((s) => s.code === b.code)) throw fail(409, "code_taken", "service code is taken");
    const id = nextId++;
    mServices.push({ ...(b as Omit<MService, "id">), id });
    return { id };
  }
  if ((m = path.match(/^\/admin\/services\/(\d+)$/))) {
    const s = mServices.find((x) => x.id === Number(m![1]));
    if (!s) throw 404;
    if (method === "DELETE") {
      if (mProducts.some((p) => p.service_id === s.id)) throw fail(409, "in_use", "service is used");
      mServices.splice(mServices.indexOf(s), 1);
    } else Object.assign(s, b);
    return ok;
  }

  if (path === "/admin/countries") {
    if (method === "GET") return mCountries;
    if (mCountries.some((c) => c.code === b.code)) throw fail(409, "code_taken", "country code is taken");
    const c = { code: b.code as string, title: b.title as I18n };
    mCountries.push(c);
    return c;
  }
  if ((m = path.match(/^\/admin\/countries\/([a-z]{2})$/))) {
    const c = mCountries.find((x) => x.code === m![1]);
    if (!c) throw 404;
    if (method === "DELETE") {
      if (mProducts.some((p) => p.variants.some((v) => v.country_code === c.code))) throw fail(409, "in_use", "country is used");
      mCountries.splice(mCountries.indexOf(c), 1);
    } else c.title = b.title as I18n;
    return ok;
  }
  throw 404;
}

// --- admin: people and orders, stateful in memory
type MUser = { id: number; name: string; language: string; roles: string[]; created_at: string; balance: string };
const mUsers: MUser[] = [
  { id: 1, name: "Сергей", language: "ru", roles: ["admin"], created_at: ago(90000), balance: "128.40" },
  { id: 2, name: "Андрей К.", language: "ru", roles: [], created_at: ago(40000), balance: "42.00" },
  { id: 3, name: "Maria", language: "en", roles: ["manager", "can_catalog"], created_at: ago(60000), balance: "0.00" },
  { id: 4, name: "Игорь", language: "ru", roles: ["executor"], created_at: ago(50000), balance: "5.00" },
  { id: 5, name: "Олег", language: "uk", roles: ["manager"], created_at: ago(30000), balance: "17.25" },
  { id: 6, name: "Дарья", language: "ru", roles: ["manager", "can_users", "can_finance"], created_at: ago(20000), balance: "0.00" },
  { id: 7, name: "Nika", language: "en", roles: ["executor"], created_at: ago(15000), balance: "0.00" },
  { id: 8, name: "Кеша", language: "ru", roles: ["executor"], created_at: ago(12000), balance: "0.00" },
  { id: 9, name: "Фёдор", language: "ru", roles: ["executor"], created_at: ago(9000), balance: "3.10" },
];
const sees = (rs: string[]) => rs.includes("admin") || rs.includes("owner") || rs.includes("can_finance");
const brief2 = (u: MUser) => ({ id: u.id, name: u.name, language: u.language, roles: u.roles });

type MExecutor = {
  id: number;
  alias: string;
  is_active: boolean;
  online: boolean;
  max_parallel: number;
  percent_override: number | null;
  permissions: { service_id: number; countries: string[] }[];
};
let selfOnline = true;
const mExecutors: MExecutor[] = [
  { id: 4, alias: "Орион", is_active: true, online: true, max_parallel: 5, percent_override: null, permissions: [{ service_id: 1, countries: ["us", "de"] }, { service_id: 2, countries: ["us"] }] },
  { id: 9, alias: "Фокс", is_active: true, online: true, max_parallel: 3, percent_override: 45, permissions: [{ service_id: 1, countries: ["us", "pl"] }] },
  { id: 7, alias: "Ника", is_active: true, online: false, max_parallel: 10, percent_override: null, permissions: [{ service_id: 2, countries: ["de", "pl", "us"] }] },
  { id: 8, alias: "Кеша", is_active: false, online: false, max_parallel: 2, percent_override: null, permissions: [] },
];

type MOrder = {
  id: number;
  status: string;
  product: string;
  variant: string;
  country: string | null;
  price: string;
  discount: string;
  created_at: string;
  buyer_id: number;
  executor_id: number | null;
  result: string;
  events: { id: number; type: string; actor_id: number | null; payload: Record<string, unknown>; created_at: string }[];
  entries: { id: number; user_id: number; account: string; kind: string; amount: string; created_at: string }[];
  /** the first assignment loses a race: someone else takes the order meanwhile */
  race?: boolean;
};
let nextEvent = 1;
const aOrder = (
  id: number,
  status: string,
  product: string,
  variant: string,
  country: string | null,
  price: string,
  buyer: number,
  executor: number | null,
  minutesAgo: number,
  extra: Partial<MOrder> = {},
): MOrder => ({
  id,
  status,
  product,
  variant,
  country,
  price,
  discount: "0.00",
  created_at: ago(minutesAgo),
  buyer_id: buyer,
  executor_id: executor,
  result: "",
  events: [
    { id: nextEvent++, type: "paid", actor_id: buyer, payload: {}, created_at: ago(minutesAgo) },
    ...(executor ? [{ id: nextEvent++, type: "assigned", actor_id: null, payload: { executor_id: executor, mode: "queue" }, created_at: ago(minutesAgo - 5) }] : []),
  ],
  entries: [{ id: nextEvent++, user_id: buyer, account: "main", kind: "purchase", amount: `-${price}`, created_at: ago(minutesAgo) }],
  ...extra,
});
const mOrders: MOrder[] = [
  aOrder(1052, "in_queue", "Регистрация Google Ads", "С верификацией", null, "45.00", 2, null, 20, { race: true }),
  aOrder(1051, "in_queue", "Аккаунт Instagram, прогретый", "30 дней", "us", "12.50", 5, null, 40),
  aOrder(1050, "assigned", "Аккаунт Instagram, прогретый", "30 дней", "us", "12.50", 2, 4, 90),
  aOrder(1049, "assigned", "Прокси, 10 штук", "Residential", "pl", "20.00", 5, 9, 150),
  aOrder(1048, "ready", "Регистрация Google Ads", "С верификацией", null, "45.00", 2, 7, 300, { result: "Аккаунт: ads-4471@example.com\nПароль: Zt9!kLm2" }),
  aOrder(1047, "awaiting_input", "Аккаунт Instagram, прогретый", "7 дней", "pl", "8.00", 5, null, 330),
  aOrder(1046, "paid", "Гайд по прогреву", "—", null, "3.00", 2, null, 400),
  aOrder(1045, "completed", "Аккаунт Facebook, старый", "С почтой", "de", "18.50", 2, null, 2000, { result: "fb_de_201:Kx19!" }),
  aOrder(1044, "completed", "Регистрация Google Ads", "С верификацией", null, "45.00", 5, 7, 3000, { result: "Аккаунт: ads-1200@example.com" }),
  aOrder(1043, "failed", "Прокси, 10 штук", "Residential", "pl", "20.00", 2, 9, 4000),
  aOrder(1042, "cancelled", "Аккаунт Facebook, старый", "—", "us", "15.00", 5, null, 5000),
  aOrder(1041, "refunded", "Аккаунт Instagram, прогретый", "30 дней", "us", "12.50", 2, 4, 6000),
];
const aliasOf = (id: number | null) => mExecutors.find((e) => e.id === id)?.alias ?? null;
const orderTotal = (o: MOrder) => price(Number(o.price) - Number(o.discount));
const ACTIONS: Record<string, string[]> = {
    in_queue: ["assign", "cancel"],
    assigned: ["assign", "refund", "cancel"],
    ready: ["confirm", "send_back", "refund"],
    awaiting_input: ["cancel"],
    paid: ["cancel"],
};
const actionsOf = (o: MOrder) => ACTIONS[o.status] ?? [];
const orderRow = (o: MOrder) => ({
  id: o.id,
  status: o.status,
  product: o.product,
  variant: o.variant,
  country: o.country,
  total: orderTotal(o),
  created_at: o.created_at,
  buyer_id: o.buyer_id,
  executor_alias: aliasOf(o.executor_id),
});
const orderEvent = (o: MOrder, type: string, payload: Record<string, unknown> = {}) =>
  o.events.push({ id: nextEvent++, type, actor_id: 1, payload, created_at: ago(0) });
const orderById = (id: number) => {
  const o = mOrders.find((x) => x.id === id);
  if (!o) throw 404;
  return o;
};
const userById = (id: number) => {
  const u = mUsers.find((x) => x.id === id);
  if (!u) throw 404;
  return u;
};

const mManagers = () => mUsers.filter((u) => u.roles.includes("manager"));

/** undefined: not one of these routes. */
function peopleRoute(method: string, path: string, body: unknown, q: URLSearchParams): unknown {
  const b = (body ?? {}) as Record<string, unknown>;
  const ok = { ok: true };
  let m: RegExpMatchArray | null;

  if (path === "/admin/users") {
    const needle = (q.get("q") ?? "").trim().toLowerCase();
    return mUsers.filter((u) => String(u.id) === needle || u.name.toLowerCase().includes(needle)).map(brief2);
  }
  if ((m = path.match(/^\/admin\/users\/(\d+)\/roles$/))) {
    const u = userById(Number(m[1]));
    if (u.roles.includes("admin") || u.roles.includes("owner")) throw fail(409, "protected", "protected role");
    for (const [flag, on] of Object.entries(b.flags as Record<string, boolean>))
      u.roles = on ? [...new Set([...u.roles, flag])] : u.roles.filter((r) => r !== flag);
    return brief2(u);
  }
  if ((m = path.match(/^\/admin\/users\/(\d+)\/balance$/))) {
    const u = userById(Number(m[1]));
    const next = Number(u.balance) + Number(b.amount);
    if (next < 0) throw fail(422, "InsufficientFunds", "Insufficient funds");
    u.balance = price(next);
    return { balance: u.balance };
  }
  if ((m = path.match(/^\/admin\/users\/(\d+)$/))) {
    const u = userById(Number(m[1]));
    return {
      ...brief2(u),
      created_at: u.created_at,
      blocked: u.id === 8,
      balance: sees(roles) ? u.balance : null,
      orders: mOrders
        .filter((o) => o.buyer_id === u.id)
        .map((o) => ({ id: o.id, status: o.status, product: o.product, total: orderTotal(o), created_at: o.created_at })),
    };
  }

  if (path === "/admin/executors") {
    if (method === "POST") {
      if (mExecutors.some((e) => e.alias === b.alias)) throw fail(409, "AliasTaken", "alias is taken");
      if (mExecutors.some((e) => e.id === b.tg_id)) throw fail(409, "ExecutorExists", "already an executor");
      mExecutors.push({ id: b.tg_id as number, alias: b.alias as string, is_active: true, online: false, max_parallel: 3, percent_override: null, permissions: [] });
      return ok;
    }
    return mExecutors.map((e) => ({
      id: e.id,
      alias: e.alias,
      is_active: e.is_active,
      online: e.online,
      in_work: mOrders.filter((o) => o.executor_id === e.id && o.status === "assigned").length,
      completed: mOrders.filter((o) => o.executor_id === e.id && o.status === "completed").length,
      avg_score: e.id === 8 ? null : 4.6,
    }));
  }
  if ((m = path.match(/^\/admin\/executors\/(\d+)\/permissions$/))) {
    const e = mExecutors.find((x) => x.id === Number(m![1]));
    if (!e) throw 404;
    e.permissions = [...e.permissions.filter((p) => p.service_id !== b.service_id), { service_id: b.service_id as number, countries: b.countries as string[] }];
    return ok;
  }
  if ((m = path.match(/^\/admin\/executors\/(\d+)$/))) {
    const e = mExecutors.find((x) => x.id === Number(m![1]));
    if (!e) throw 404;
    if (method === "PATCH") return Object.assign(e, b), ok;
    return {
      ...e,
      name: userById(e.id).name,
      stats: { completed: 41, failed: 1, overdue: 2, refused: 3, avg_minutes: 54.4, avg_score: 4.8 },
      wallet: { hold: "12.40", available: "58.75", wallet: "TQrZ9sT3xJ4kLw8vUe2Yb7NcMdHfPa6GhV" },
    };
  }

  if (path === "/admin/managers") {
    if (method === "POST") {
      const id = b.tg_id as number;
      const u = mUsers.find((x) => x.id === id);
      if (u?.roles.includes("manager")) throw fail(409, "ManagerExists", "already a manager");
      if (u) u.roles = [...u.roles, "manager"];
      else mUsers.push({ id, name: `User ${id}`, language: "ru", roles: ["manager"], created_at: ago(1), balance: "0.00" });
      return ok;
    }
    return mManagers().map(brief2);
  }
  if ((m = path.match(/^\/admin\/managers\/(\d+)$/))) {
    const u = userById(Number(m[1]));
    u.roles = u.roles.filter((r) => r !== "manager" && !r.startsWith("can_"));
    return ok;
  }
  if (path === "/staff/managers") return mManagers().map((u) => ({ id: u.id, name: u.name, admin: false })).concat([{ id: 1, name: "Сергей", admin: true }]);
  if ((m = path.match(/^\/tickets\/(\d+)\/handover$/))) {
    const tk = tickets.find((x) => x.id === Number(m![1]));
    if (!tk || tk.status === "closed") throw 404;
    tk.mine = false;
    return ok;
  }

  if (path === "/admin/orders") {
    const status = q.get("status");
    const buyer = q.get("buyer_id");
    const rows = mOrders.filter((o) => (!status || o.status === status) && (!buyer || o.buyer_id === Number(buyer)));
    return { items: rows.map(orderRow), total: rows.length, page: Number(q.get("page") ?? 0), page_size: 20 };
  }
  if ((m = path.match(/^\/admin\/orders\/(\d+)\/executors$/))) {
    const o = orderById(Number(m[1]));
    return mExecutors
      .filter((e) => e.is_active)
      .map((e) => ({
        id: e.id,
        alias: e.alias,
        load: mOrders.filter((x) => x.executor_id === e.id && x.status === "assigned").length,
        max_parallel: e.max_parallel,
        online: e.online,
        current: e.id === o.executor_id,
      }));
  }
  if ((m = path.match(/^\/admin\/orders\/(\d+)\/assign$/))) {
    const o = orderById(Number(m[1]));
    if (o.race) {
      o.race = false;
      o.executor_id = 7;
      o.status = "assigned";
      orderEvent(o, "assigned", { executor_id: 7 });
      throw fail(409, "changed", "the order changed");
    }
    if (b.expected_executor_id !== o.executor_id) throw fail(409, "changed", "the order changed");
    if (b.executor_id === o.executor_id) throw fail(409, "same_executor", "same executor");
    orderEvent(o, o.executor_id ? "reassigned" : "assigned", { executor_id: b.executor_id, from: o.executor_id });
    o.executor_id = b.executor_id as number;
    o.status = "assigned";
    return ok;
  }
  if ((m = path.match(/^\/admin\/orders\/(\d+)\/refund$/))) {
    const o = orderById(Number(m[1]));
    o.status = b.reason === "cancel" ? "cancelled" : "failed";
    o.entries.push({ id: nextEvent++, user_id: o.buyer_id, account: "main", kind: "refund", amount: orderTotal(o), created_at: ago(0) });
    orderEvent(o, "refund", { reason: b.reason });
    return { order_id: o.id, refunded: orderTotal(o) };
  }
  if ((m = path.match(/^\/admin\/orders\/(\d+)$/))) {
    const o = orderById(Number(m[1]));
    return {
      ...orderRow(o),
      buyer_name: userById(o.buyer_id).name,
      executor_id: o.executor_id,
      price: o.price,
      discount: o.discount,
      assigned_at: o.executor_id ? ago(30) : null,
      deadline_at: o.status === "assigned" ? minutes(60) : null,
      ready_at: o.status === "ready" || o.status === "completed" ? ago(20) : null,
      completed_at: o.status === "completed" ? ago(10) : null,
      fields: [
        { label: "Почта для регистрации", value: "buyer.mail@example.com", is_file: false },
        { label: "Паспорт", value: null, is_file: true },
      ],
      result: o.result,
      result_files: o.status === "ready" ? 1 : 0,
      events: o.events,
      entries: o.entries,
      actions: actionsOf(o),
    };
  }
  if ((m = path.match(/^\/staff\/orders\/(\d+)\/(confirm|send_back)$/))) {
    const o = mOrders.find((x) => x.id === Number(m![1]));
    if (!o) return undefined;
    o.status = m[2] === "confirm" ? "completed" : "assigned";
    orderEvent(o, m[2] === "confirm" ? "status" : "sent_back", m[2] === "confirm" ? { to: "completed" } : { comment: (b.comment as string) ?? "" });
    return ok;
  }
  return undefined;
}

// --- admin: money, promo, broadcasts, stats, settings, audit; stateful in memory
type MWithdrawal = {
  id: number;
  executor_id: number;
  alias: string;
  name: string;
  amount: string;
  address: string;
  status: string;
  tx_hash: string | null;
  reject_reason: string | null;
  created_at: string;
  processed_at: string | null;
};
const wd = (id: number, executor: number, alias: string, name: string, amount: string, status: string, m: number, extra: Partial<MWithdrawal> = {}): MWithdrawal => ({
  id,
  executor_id: executor,
  alias,
  name,
  amount,
  address: `TQrZ9sT3xJ4kLw8vUe2Yb7NcMdHfPa6G${id}x`,
  status,
  tx_hash: null,
  reject_reason: null,
  created_at: ago(m),
  processed_at: status === "pending" ? null : ago(m - 30),
  ...extra,
});
const mWithdrawals: MWithdrawal[] = [
  wd(14, 4, "Орион", "Игорь", "58.75", "pending", 120),
  wd(13, 9, "Фокс", "Фёдор", "21.00", "pending", 600),
  wd(12, 7, "Ника", "Nika", "140.20", "pending", 1500),
  wd(11, 4, "Орион", "Игорь", "25.00", "paid", 4000, { tx_hash: "0x9f3a1c5be27d44aa90e1" }),
  wd(10, 9, "Фокс", "Фёдор", "12.00", "rejected", 6000, { reject_reason: "Неверный адрес кошелька" }),
];

type MPromo = {
  id: number;
  code: string;
  discount_percent: number | null;
  discount_amount: string | null;
  bonus_amount: string | null;
  usage_limit: number | null;
  expires_at: string | null;
  product_id: number | null;
  min_amount: string | null;
  new_users_only: boolean;
  allowed_user_ids: number[];
  reusable: boolean;
  active: boolean;
  usages: { user_id: number; name: string; order_id: number | null; created_at: string }[];
};
const promoBase = { usage_limit: null, expires_at: null, product_id: null, min_amount: null, new_users_only: false, allowed_user_ids: [], reusable: false, active: true, discount_percent: null, discount_amount: null, bonus_amount: null };
const mPromos: MPromo[] = [
  { ...promoBase, id: 1, code: "WELCOME10", discount_percent: 10, usage_limit: 100, new_users_only: true, usages: [{ user_id: 2, name: "Андрей К.", order_id: 1050, created_at: ago(900) }] },
  { ...promoBase, id: 2, code: "SUMMER5", discount_amount: "5.00", expires_at: minutes(60 * 24 * 10), usage_limit: 20, usages: [] },
  { ...promoBase, id: 3, code: "BONUS3", bonus_amount: "3.00", reusable: true, active: false, usages: [] },
];
const promoKind = (p: MPromo) =>
  p.discount_percent !== null
    ? { kind: "percent", value: String(p.discount_percent) }
    : p.discount_amount !== null
      ? { kind: "amount", value: price(p.discount_amount) }
      : { kind: "bonus", value: price(p.bonus_amount ?? 0) };
const promoBrief = (p: MPromo) => ({
  id: p.id,
  code: p.code,
  ...promoKind(p),
  times_used: p.usages.length,
  usage_limit: p.usage_limit,
  expires_at: p.expires_at,
  active: p.active,
});

type MBroadcast = {
  id: number;
  text: string;
  status: string;
  sent_count: number;
  failed_count: number;
  total_count: number | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
};
const mBroadcasts: MBroadcast[] = [
  { id: 3, text: "Новые прокси уже в каталоге. Загляните в раздел «Прокси».", status: "draft", sent_count: 0, failed_count: 0, total_count: null, created_at: ago(30), started_at: null, finished_at: null },
  { id: 2, text: "Скидка 10% по коду WELCOME10 до конца недели.", status: "sent", sent_count: 412, failed_count: 9, total_count: 421, created_at: ago(3000), started_at: ago(2990), finished_at: ago(2985) },
  { id: 1, text: "Технические работы сегодня ночью.", status: "stopped", sent_count: 80, failed_count: 1, total_count: 421, created_at: ago(9000), started_at: ago(8990), finished_at: ago(8988) },
];
/** Every read of a running broadcast moves it on, so the polling shows progress. */
function advance(b: MBroadcast) {
  if (b.status !== "sending" || b.total_count === null) return b;
  b.sent_count = Math.min(b.total_count, b.sent_count + 60);
  if (b.sent_count >= b.total_count) (b.status = "sent"), (b.finished_at = ago(0));
  return b;
}
const broadcastById = (id: number) => {
  const b = mBroadcasts.find((x) => x.id === id);
  if (!b) throw 404;
  return b;
};

let mSettings = { hold_days: 7, review_delay_hours: 24, min_withdrawal: "10.00" };
const mAudit = [
  { id: 6, actor_id: 1, actor_name: "Сергей", action: "withdrawal.pay", target: "withdrawal:11", payload: { tx_hash: "0x9f3a…" }, created_at: ago(4000) },
  { id: 5, actor_id: 3, actor_name: "Maria", action: "catalog.product.update", target: "product:2", payload: { is_active: true }, created_at: ago(3500) },
  { id: 4, actor_id: 1, actor_name: "Сергей", action: "balance.adjust", target: "user:2", payload: { amount: "25.00", comment: "Компенсация" }, created_at: ago(2000) },
  { id: 3, actor_id: 6, actor_name: "Дарья", action: "executor.set_permissions", target: "executor:9", payload: { service: "socials", countries: ["us", "pl"] }, created_at: ago(1500) },
  { id: 2, actor_id: 1, actor_name: "Сергей", action: "settings.update", target: null, payload: { hold_days: 7 }, created_at: ago(900) },
  { id: 1, actor_id: null, actor_name: null, action: "order.assign", target: "order:1050", payload: { executor_id: 4 }, created_at: ago(90) },
];

/** undefined: not one of these routes. */
function financeRoute(method: string, path: string, body: unknown, q: URLSearchParams): unknown {
  const b = (body ?? {}) as Record<string, unknown>;
  const ok = { ok: true };
  let m: RegExpMatchArray | null;

  if (path === "/admin/withdrawals") return mWithdrawals.filter((w) => w.status === (q.get("status") ?? "pending"));
  if ((m = path.match(/^\/admin\/withdrawals\/(\d+)\/(pay|reject)$/))) {
    const w = mWithdrawals.find((x) => x.id === Number(m![1]));
    if (!w) throw 404;
    if (w.status !== "pending") throw fail(409, "not_pending", "already processed");
    w.status = m[2] === "pay" ? "paid" : "rejected";
    w.processed_at = ago(0);
    if (m[2] === "pay") w.tx_hash = b.tx_hash as string;
    else w.reject_reason = b.reason as string;
    return { changed: true };
  }

  if (path === "/admin/promos") {
    if (method === "GET") return mPromos.map(promoBrief);
    if (mPromos.some((p) => p.code === b.code)) throw fail(409, "code_taken", "promo code is taken");
    const kinds = ["discount_percent", "discount_amount", "bonus_amount"].filter((k) => b[k] !== null && b[k] !== undefined);
    if (kinds.length !== 1) throw fail(422, "InvalidField", "exactly one of percent, amount or bonus", "kind");
    const id = nextId++;
    mPromos.push({ ...promoBase, ...(b as Partial<MPromo>), id, code: b.code as string, usages: [] });
    return { id };
  }
  if ((m = path.match(/^\/admin\/promos\/(\d+)$/))) {
    const p = mPromos.find((x) => x.id === Number(m![1]));
    if (!p) throw 404;
    if (method === "PATCH") {
      Object.assign(p, b);
      return ok;
    }
    return { ...promoBrief(p), ...p, usages: p.usages };
  }

  if (path === "/admin/broadcasts/recipients") return { count: 421 };
  if (path === "/admin/broadcasts/preview") return ok;
  if (path === "/admin/broadcasts") {
    if (method === "GET") return [...mBroadcasts].sort((x, y) => y.id - x.id);
    const id = nextId++;
    mBroadcasts.push({ id, text: b.text as string, status: "draft", sent_count: 0, failed_count: 0, total_count: null, created_at: ago(0), started_at: null, finished_at: null });
    return { id };
  }
  if ((m = path.match(/^\/admin\/broadcasts\/(\d+)\/(start|stop)$/))) {
    const x = broadcastById(Number(m[1]));
    if (m[2] === "start") Object.assign(x, { status: "sending", total_count: 421, started_at: ago(0) });
    else Object.assign(x, { status: "stopped", finished_at: ago(0) });
    return x;
  }
  if ((m = path.match(/^\/admin\/broadcasts\/(\d+)$/))) {
    const x = broadcastById(Number(m[1]));
    if (method === "PUT") return (x.text = b.text as string), ok;
    return { ...advance(x) };
  }

  if (path === "/admin/stats") {
    const days = Number(q.get("days") ?? 7);
    const k = days === 1 ? 0.15 : days === 7 ? 1 : 4.2;
    const sum = (n: number) => price(n * k);
    return {
      days,
      revenue: sum(1240),
      refunds: sum(95),
      topups: sum(1500),
      paid_out: sum(410),
      orders: { completed: Math.round(48 * k), assigned: 6, in_queue: 3, ready: 2, failed: Math.round(2 * k), cancelled: Math.round(4 * k) },
      top: [
        { product_id: 2, title: "Аккаунт Instagram, прогретый", orders: Math.round(21 * k), revenue: sum(520) },
        { product_id: 6, title: "Регистрация Google Ads", orders: Math.round(9 * k), revenue: sum(405) },
        { product_id: 1, title: "Аккаунт Facebook, старый", orders: Math.round(11 * k), revenue: sum(180) },
        { product_id: 4, title: "Прокси, 10 штук", orders: Math.round(6 * k), revenue: sum(120) },
      ],
      hold: "112.40",
      available: "358.75",
      buyers: "2480.10",
      buyers_hold: "86.00",
    };
  }
  if (path === "/admin/settings") {
    if (method === "PUT") mSettings = { ...mSettings, ...(b as typeof mSettings) };
    return mSettings;
  }
  if (path === "/admin/audit/actions") return [...new Set(mAudit.map((r) => r.action))];
  if (path === "/admin/audit") {
    const actor = q.get("actor_id");
    const action = q.get("action");
    return mAudit.filter((r) => (!actor || r.actor_id === Number(actor)) && (!action || r.action === action));
  }
  return undefined;
}

function route(method: string, url: URL, body: unknown): unknown {
  const path = url.pathname.replace(/^\/api/, "");
  const q = url.searchParams;
  let m: RegExpMatchArray | null;
  const people = peopleRoute(method, path, body, q);
  if (people !== undefined) return people;
  const finance = financeRoute(method, path, body, q);
  if (finance !== undefined) return finance;
  if (path.startsWith("/admin/")) return adminRoute(method, path, body);
  if (path === "/me")
    return {
      id: 1,
      name: "Сергей",
      language: query.get("lang") ?? "ru",
      roles,
      balance: "128.40",
      hold: "12.50",
      executor: roles.includes("executor") ? { hold: "12.40", available: "58.75" } : null,
    };
  if (path === "/unread") return { orders: 2, support: 1, work: 1, tickets: 2, review: 1 };
  if (path.match(/^\/conversations\/\d+\/read$/)) return { ok: true };
  if (path === "/orders") return { items: orders.map(brief), total: orders.length, page: 0, page_size: 20 };
  if ((m = path.match(/^\/orders\/(\d+)$/))) {
    const o = orders.find((x) => x.id === Number(m![1]));
    if (!o) throw 404;
    const done = o.status === "completed";
    return { ...brief(o), executor_alias: o.alias, result: done ? o.result : null, result_files: o.id === 1030 ? 2 : 0, can_cancel: !!o.cancel, reserved: ["in_queue", "assigned", "ready"].includes(o.status) ? o.total : null, extension: o.status === "assigned" ? { request_id: 1, minutes: 60, until: minutes(120) } : null };
  }
  if ((m = path.match(/^\/orders\/(\d+)\/cancel$/))) {
    const o = orders.find((x) => x.id === Number(m![1]));
    if (o) (o.status = "cancelled"), (o.cancel = false);
    return { order_id: Number(m[1]), refunded: o?.total ?? "0.00" };
  }
  if (path === "/balance")
    return {
      balance: "128.40",
      hold: "12.50",
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

  if (path === "/executor/online") {
    if (method === "PUT") selfOnline = (body as { online: boolean }).online;
    return { online: selfOnline };
  }
  if (path === "/executor/queue") return queue;
  if ((m = path.match(/^\/executor\/orders\/(\d+)\/take$/))) return execDetail(Number(m[1]));
  if (path === "/executor/orders") return { items: execOrders, total: execOrders.length, page: 0, page_size: 20 };
  if ((m = path.match(/^\/executor\/orders\/(\d+)\/(refuse|result|extension)$/))) return m[2] === "refuse" ? { ok: true } : execDetail(Number(m[1]));
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
  if ((m = path.match(/^\/tickets\/(\d+)$/))) return tickets.find((x) => x.id === Number(m![1])) ?? tickets[0];
  if (path.match(/^\/tickets\/\d+\/(take|close)$/)) return path.endsWith("take") ? { conversation_id: 3 } : { ok: true };
  if (path === "/staff/orders") return orders.filter((o) => o.status === "ready").map((o) => ({ ...brief(o), executor_id: 7, ready_at: ago(25) }));
  if ((m = path.match(/^\/staff\/orders\/(\d+)$/))) {
    const o = orders.find((x) => x.id === Number(m![1])) ?? orders[2];
    return {
      ...brief(o),
      executor_id: 7,
      executor_alias: o.alias,
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
    if (typeof e === "object" && e !== null && "status" in e) {
      const f = e as Fail;
      return Response.json(f.body, { status: f.status });
    }
    throw e;
  }
};

export {};
