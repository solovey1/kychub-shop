import { useCallback, useEffect, useRef, useState, useSyncExternalStore } from "react";
import { useLive } from "./live";
import { initData } from "./telegram";

export type Status =
  | "awaiting_input"
  | "paid"
  | "in_queue"
  | "assigned"
  | "ready"
  | "completed"
  | "failed"
  | "refunded"
  | "cancelled";

// Money is a string ("12.50"), time is ISO 8601 UTC. Mirrors app/presentation/fastapi/api/schemas.py.
export type Me = {
  id: number;
  name: string;
  language: string;
  roles: string[];
  balance: string;
  executor: { hold: string; available: string } | null;
};
export type OrderBrief = {
  id: number;
  status: Status;
  product: string;
  variant: string;
  country: string | null;
  total: string;
  created_at: string;
  unread: number;
};
export type Order = OrderBrief & {
  executor_alias: string | null;
  result: string | null;
  result_files: number;
  can_cancel: boolean;
};
export type Page<T> = { items: T[]; total: number; page: number; page_size: number };
export type Entry = {
  id: number;
  kind: string;
  amount: string;
  balance_after: string;
  order_id: number | null;
  created_at: string;
};
export type Balance = { balance: string; entries: Entry[] };
export type Message = {
  id: number;
  sender_role: string;
  mine: boolean;
  text: string | null;
  media_type: string | null;
  created_at: string;
};
export type Messages = { items: Message[]; has_more: boolean; can_post: boolean };
export type CardField = { label: string; value: string | null; is_file: boolean };
export type ResultField = {
  key: string;
  label: string;
  type: string;
  required: boolean;
  options: string[] | null;
  max_length: number;
};
export type QueueItem = {
  id: number;
  status: Status;
  product: string;
  country: string | null;
  earning: string;
  deadline_minutes: number;
};
export type ExecutorOrder = QueueItem & {
  deadline_at: string | null;
  fields: CardField[];
  result_form: ResultField[] | null;
  result: Record<string, string> | null;
};
export type ExecutorListItem = {
  id: number;
  status: Status;
  product: string;
  variant: string;
  country: string | null;
  deadline_at: string | null;
  unread: number;
};
export type Stats = {
  completed: number;
  failed: number;
  overdue: number;
  refused: number;
  avg_minutes: number | null;
  avg_score: number | null;
};
export type Wallet = {
  hold: string;
  available: string;
  wallet: string | null;
  minimum: string;
  entries: Entry[];
};
export type Ticket = {
  id: number;
  status: "open" | "taken" | "closed";
  order_id: number | null;
  buyer_name: string;
  mine: boolean;
  conversation_id: number;
  created_at: string;
  unread: number;
};
export type StaffOrderBrief = OrderBrief & { executor_id: number | null; ready_at: string | null };
export type StaffOrder = StaffOrderBrief & {
  executor_alias: string | null;
  earning: string;
  fields: CardField[];
  result: string;
  result_files: number;
};

// The admin API (app/presentation/fastapi/api/admin/schemas.py). Texts are {ru, en, uk}, `ru` required.
export type I18n = Record<string, string>;
export type AdminCategory = {
  id: number;
  parent_id: number | null;
  title: I18n;
  position: number;
  is_active: boolean;
  children: number;
  products: number;
};
export type Fulfillment = "stock" | "fixed" | "manual" | "executor";
export type AdminProductBrief = {
  id: number;
  title: I18n;
  is_active: boolean;
  fulfillment_type: Fulfillment;
  variants: number;
  price_from: string | null;
};
export type FieldType = "text" | "email" | "number" | "choice" | "login" | "file";
export type SchemaField = {
  key: string;
  label: I18n;
  type: FieldType;
  required: boolean;
  regex?: string;
  options?: string[];
  hidden_from_executor?: boolean;
  hint?: I18n;
  placeholder?: I18n;
  max_length?: number;
};
export type FormSchema = { fields?: SchemaField[] };
export type AdminVariant = {
  id: number;
  country_code: string | null;
  title: I18n | null;
  price: string;
  is_active: boolean;
  stock: number | null;
};
export type AdminProduct = {
  id: number;
  category_id: number;
  service_id: number | null;
  title: I18n;
  description: I18n;
  input_schema: FormSchema;
  result_schema: FormSchema;
  fulfillment_type: Fulfillment;
  fulfillment_config: { text?: string };
  is_active: boolean;
  variants: AdminVariant[];
  used: "has_orders" | "has_promo" | null;
};
export type AdminStock = {
  free: number;
  unlimited: string | null;
  recent: { id: number; payload: string }[];
};
export type AdminService = {
  id: number;
  code: string;
  title: string;
  deadline_minutes: number;
  assign_mode: "queue" | "auto";
  executor_percent: number;
  is_active: boolean;
};
export type AdminCountry = { code: string; title: I18n };

export type UserBrief = { id: number; name: string; language: string; roles: string[] };
export type UserCard = UserBrief & {
  created_at: string;
  blocked: boolean;
  /** null: the viewer may not see money */
  balance: string | null;
  orders: { id: number; status: Status; product: string; total: string; created_at: string }[];
};
export type ExecutorRow = {
  id: number;
  alias: string;
  is_active: boolean;
  in_work: number;
  completed: number;
  avg_score: number | null;
};
export type ExecutorDetail = {
  id: number;
  alias: string;
  name: string;
  is_active: boolean;
  max_parallel: number;
  percent_override: number | null;
  permissions: { service_id: number; countries: string[] }[];
  stats: Stats;
  wallet: { hold: string; available: string; wallet: string | null };
};
export type AdminOrderRow = {
  id: number;
  status: Status;
  product: string;
  variant: string;
  country: string | null;
  total: string;
  created_at: string;
  buyer_id: number;
  executor_alias: string | null;
};
export type AdminOrder = AdminOrderRow & {
  buyer_name: string;
  executor_id: number | null;
  price: string;
  discount: string;
  assigned_at: string | null;
  deadline_at: string | null;
  ready_at: string | null;
  completed_at: string | null;
  fields: CardField[];
  result: string;
  result_files: number;
  events: { id: number; type: string; actor_id: number | null; payload: Record<string, unknown>; created_at: string }[];
  entries: { id: number; user_id: number; account: string; kind: string; amount: string; created_at: string }[];
  actions: string[];
};
export type Assignable = { id: number; alias: string; load: number; max_parallel: number; current: boolean };
export type Withdrawal = {
  id: number;
  executor_id: number;
  alias: string | null;
  name: string;
  amount: string;
  address: string;
  status: "pending" | "paid" | "rejected";
  tx_hash: string | null;
  reject_reason: string | null;
  created_at: string;
  processed_at: string | null;
};
export type PromoKind = "percent" | "amount" | "bonus";
export type PromoBrief = {
  id: number;
  code: string;
  kind: PromoKind;
  value: string;
  times_used: number;
  usage_limit: number | null;
  expires_at: string | null;
  active: boolean;
};
export type Promo = PromoBrief & {
  discount_percent: number | null;
  discount_amount: string | null;
  bonus_amount: string | null;
  product_id: number | null;
  min_amount: string | null;
  new_users_only: boolean;
  allowed_user_ids: number[];
  reusable: boolean;
  usages: { user_id: number; name: string; order_id: number | null; created_at: string }[];
};
export type Broadcast = {
  id: number;
  text: string;
  status: "draft" | "sending" | "sent" | "stopped";
  sent_count: number;
  failed_count: number;
  total_count: number | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
};
export type StatsData = {
  days: number;
  revenue: string;
  refunds: string;
  topups: string;
  paid_out: string;
  orders: Record<string, number>;
  top: { product_id: number; title: string; orders: number; revenue: string }[];
  hold: string;
  available: string;
  buyers: string;
};
export type Tunables = { hold_days: number; review_delay_hours: number; min_withdrawal: string };
export type AuditRow = {
  id: number;
  actor_id: number | null;
  actor_name: string | null;
  action: string;
  target: string | null;
  payload: Record<string, unknown>;
  created_at: string;
};
export type StaffMember = { id: number; name: string; admin: boolean };

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string | null,
    public detail: string,
    public field: string | null = null,
  ) {
    super(detail);
  }
}

let expired = false;
const watchers = new Set<() => void>();
export const useExpired = () =>
  useSyncExternalStore(
    (cb) => (watchers.add(cb), () => void watchers.delete(cb)),
    () => expired,
  );

async function request(method: string, path: string, body?: unknown): Promise<Response> {
  const res = await fetch(`/api${path}`, {
    method,
    headers: {
      Authorization: `tma ${initData}`,
      ...(body === undefined ? {} : { "Content-Type": "application/json" }),
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (res.ok) return res;
  if (res.status === 401) {
    expired = true;
    watchers.forEach((w) => w());
  }
  let code: string | null = null;
  let detail = res.statusText;
  let field: string | null = null;
  try {
    const json = await res.json();
    code = typeof json.code === "string" ? json.code : null;
    detail = typeof json.detail === "string" ? json.detail : JSON.stringify(json.detail);
    field = typeof json.field === "string" ? json.field : null;
  } catch {
    // not JSON: keep the status text
  }
  throw new ApiError(res.status, code, detail, field);
}

export const get = async <T>(path: string): Promise<T> => (await request("GET", path)).json();
export const send = async <T>(
  method: "POST" | "PUT" | "PATCH" | "DELETE",
  path: string,
  body?: unknown,
): Promise<T> => (await request(method, path, body ?? {})).json();

/** A file behind the auth header as a blob: URL, the caller revokes it. */
export async function blobUrl(path: string): Promise<string> {
  return URL.createObjectURL(await (await request("GET", path)).blob());
}

export type Loaded<T> = { data: T | undefined; error: ApiError | undefined; reload: () => void };

/** GET `path` (null: not yet). The data stays while it reloads; `live` event types trigger a reload. */
export function useFetch<T>(path: string | null, live: string[] = []): Loaded<T> {
  const [data, setData] = useState<T>();
  const [error, setError] = useState<ApiError>();
  const seq = useRef(0);
  const load = useCallback(() => {
    if (path === null) return;
    const id = ++seq.current;
    get<T>(path).then(
      (d) => id === seq.current && (setData(d), setError(undefined)),
      (e: ApiError) => id === seq.current && setError(e),
    );
  }, [path]);
  useEffect(() => {
    setData(undefined);
    setError(undefined);
    load();
  }, [load]);
  useLive(live, load);
  return { data, error, reload: load };
}

/** A paged list (`page` query): «show more» appends, a reload refreshes the first page in place. */
export function usePaged<T extends { id: number }>(path: string, live: string[]) {
  const [items, setItems] = useState<T[]>();
  const [total, setTotal] = useState(0);
  const [error, setError] = useState<ApiError>();
  const next = useRef(1);
  const load = useCallback(
    (page: number) =>
      get<Page<T>>(`${path}${path.includes("?") ? "&" : "?"}page=${page}`).then(
        (r) => {
          setTotal(r.total);
          setError(undefined);
          if (page === 0) {
            setItems((old) => [
              ...r.items,
              ...(old ?? []).filter((o) => !r.items.some((i) => i.id === o.id)),
            ]);
          } else {
            next.current = page + 1;
            setItems((old) => [
              ...(old ?? []),
              ...r.items.filter((i) => !old?.some((o) => o.id === i.id)),
            ]);
          }
        },
        (e: ApiError) => setError(e),
      ),
    [path],
  );
  useEffect(() => {
    next.current = 1;
    setItems(undefined);
    void load(0);
  }, [load]);
  useLive(live, () => void load(0));
  return { items, total, error, more: () => load(next.current), reload: () => load(0) };
}
