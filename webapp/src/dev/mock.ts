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

function route(method: string, url: URL, body: unknown): unknown {
  const path = url.pathname.replace(/^\/api/, "");
  const q = url.searchParams;
  let m: RegExpMatchArray | null;
  if (path.startsWith("/admin/")) return adminRoute(method, path, body);
  if (path === "/me")
    return {
      id: 1,
      name: "Сергей",
      language: query.get("lang") ?? "ru",
      roles,
      balance: "128.40",
      executor: roles.includes("executor") ? { hold: "12.40", available: "58.75" } : null,
    };
  if (path === "/unread") return { orders: 2, support: 1, work: 1, tickets: 2, review: 1 };
  if (path.match(/^\/conversations\/\d+\/read$/)) return { ok: true };
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
