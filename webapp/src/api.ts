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
};
export type StaffOrderBrief = OrderBrief & { executor_id: number | null; ready_at: string | null };
export type StaffOrder = StaffOrderBrief & {
  earning: string;
  fields: CardField[];
  result: string;
  result_files: number;
};

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string | null,
    public detail: string,
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
  try {
    const json = await res.json();
    code = typeof json.code === "string" ? json.code : null;
    detail = typeof json.detail === "string" ? json.detail : JSON.stringify(json.detail);
  } catch {
    // not JSON: keep the status text
  }
  throw new ApiError(res.status, code, detail);
}

export const get = async <T>(path: string): Promise<T> => (await request("GET", path)).json();
export const send = async <T>(method: "POST" | "PUT", path: string, body?: unknown): Promise<T> =>
  (await request(method, path, body ?? {})).json();

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
      get<Page<T>>(`${path}?page=${page}`).then(
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
