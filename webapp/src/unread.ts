import { useEffect, useSyncExternalStore } from "react";
import { get } from "./api";
import { useLive } from "./live";

/** `orders` and `work` count DISTINCT orders (unread chat or something to do), so tabs add them
 * to `support` / `offers` without counting an order twice. `*_action` is the "to do" part alone. */
export type Unread = {
  orders: number; // buyer: orders with an unread chat or waiting for him
  support: number;
  work: number; // executor: own orders with an unread chat, assigned, or a dispute to answer
  tickets: number;
  review: number;
  disputes: number;
  orders_action: number;
  work_action: number;
  offers: number; // executor: queue orders he may take now
};

let state: Unread | undefined;
const watchers = new Set<() => void>();
let timer: ReturnType<typeof setTimeout> | undefined;

function load() {
  get<Unread>("/unread").then(
    (d) => ((state = d), watchers.forEach((w) => w())),
    () => {
      // the counters are decoration: the next event tries again
    },
  );
}

/** Reload the counters, at most once per 500 ms. */
export function refreshUnread() {
  clearTimeout(timer);
  timer = setTimeout(load, 500);
}

/** Keeps the counters fresh; mounted once, by the shell. */
export function useUnreadFeed() {
  useEffect(load, []);
  useLive(["message", "order", "ticket", "queue"], refreshUnread);
}

const NONE: Unread = { orders: 0, support: 0, work: 0, tickets: 0, review: 0, disputes: 0, orders_action: 0, work_action: 0, offers: 0 };
export const useUnread = (): Unread =>
  useSyncExternalStore(
    (cb) => (watchers.add(cb), () => void watchers.delete(cb)),
    () => state,
  ) ?? NONE;
