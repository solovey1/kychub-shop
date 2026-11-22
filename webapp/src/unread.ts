import { useEffect, useSyncExternalStore } from "react";
import { get } from "./api";
import { useLive } from "./live";

export type Unread = { orders: number; support: number; work: number; tickets: number; review: number };

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

const NONE: Unread = { orders: 0, support: 0, work: 0, tickets: 0, review: 0 };
export const useUnread = (): Unread =>
  useSyncExternalStore(
    (cb) => (watchers.add(cb), () => void watchers.delete(cb)),
    () => state,
  ) ?? NONE;
