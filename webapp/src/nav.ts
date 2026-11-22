// History depth of the app. Every entry the app makes carries its index, so «is there anything to go
// back to» is an answer, not a guess: index 0 is the screen the app was opened on (a bot button with
// ?to=), where «back» has to lead to the parent screen instead of out of the app.
const index = () => (history.state as { idx?: number } | null)?.idx ?? 0;
const push = history.pushState.bind(history);
const replace = history.replaceState.bind(history);
history.pushState = (_state, title, url) => push({ idx: index() + 1 }, title, url);
history.replaceState = (_state, title, url) => replace({ idx: index() }, title, url);

export const canGoBack = () => index() > 0;

const PARENTS: [RegExp, (m: RegExpMatchArray) => string][] = [
  [/^\/work\/order\/(\d+)\/chat\//, (m) => `/work/order/${m[1]}`],
  [/^\/(chat|orders)\//, () => "/orders"],
  [/^\/ticket\//, () => "/support/tickets"],
  [/^\/work\/order\//, () => "/work/mine"],
  [/^\/work\/offer\//, () => "/work/queue"],
  [/^\/support\/review\//, () => "/support/review"],
  [/^\/admin\/catalog\/p\/(\d+)\/v\/(\d+)\/stock$/, (m) => `/admin/catalog/p/${m[1]}/v/${m[2]}`],
  [/^\/admin\/catalog\/p\/(\d+)\/v\//, (m) => `/admin/catalog/p/${m[1]}`],
  [/^\/admin\/catalog\/c\/(\d+)\/edit$/, (m) => `/admin/catalog/c/${m[1]}`],
  [/^\/admin\/orders\/(\d+)\/assign$/, (m) => `/admin/orders/${m[1]}`],
  [/^\/admin\/orders\/\d+$/, () => "/admin/orders"],
  [/^\/admin\/people\/e\//, () => "/admin/people/executors"],
  [/^\/admin\/people\/u\//, () => "/admin/people"],
  [/^\/admin\/people\/(executors|managers)$/, () => "/admin"],
  [/^\/admin\/catalog\/s\//, () => "/admin/catalog/services"],
  [/^\/admin\/catalog\/k\//, () => "/admin/catalog/countries"],
  [/^\/admin\/catalog\/(services|countries)$/, () => "/admin"],
  [/^\/admin\/catalog\/(c|p)\//, () => "/admin/catalog"],
  [/^\/admin\//, () => "/admin"],
];

/** The screen «back» leads to when the history has nothing before this one. */
export function parentOf(path: string): string {
  for (const [re, to] of PARENTS) {
    const m = path.match(re);
    if (m) return to(m);
  }
  return "/orders";
}

/** The tab a screen belongs to (a chat opened from the bot has no tab of its own). */
export function sectionOf(path: string): string {
  if (/^\/(chat)\//.test(path)) return "orders";
  if (path.startsWith("/ticket/")) return "support";
  return path.split("/")[1] ?? "";
}
