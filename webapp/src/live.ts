import { useEffect, useRef } from "react";
import { initData } from "./telegram";

export type LiveEvent = { type: string; [key: string]: unknown };
const listeners = new Set<(e: LiveEvent) => void>();
let socket: WebSocket | undefined;
let delay = 1000;
let stopped = false;

/** One socket for the whole app: the first frame carries initData (never the URL). Close 4401
 * (stale session) and 4409 (opened elsewhere) are final, anything else reconnects after 1, 2, 4... 30 s. */
export function startLive() {
  if (socket || stopped || !initData || (import.meta.env.DEV && initData === "mock")) return;
  const proto = location.protocol === "https:" ? "wss" : "ws";
  const ws = new WebSocket(`${proto}://${location.host}/api/ws`);
  socket = ws;
  ws.onopen = () => ws.send(JSON.stringify({ type: "auth", init_data: initData }));
  ws.onmessage = (m) => {
    delay = 1000;
    const event: LiveEvent = JSON.parse(m.data);
    if (event.type !== "ping") listeners.forEach((l) => l(event));
  };
  ws.onclose = (c) => {
    socket = undefined;
    if (c.code === 4401 || c.code === 4409) return void (stopped = true);
    setTimeout(startLive, delay);
    delay = Math.min(delay * 2, 30000);
  };
}

export function useLive(types: string[], fn: (e: LiveEvent) => void) {
  const latest = useRef(fn);
  latest.current = fn;
  const key = types.join();
  useEffect(() => {
    if (!key) return;
    const wanted = key.split(",");
    const l = (e: LiveEvent) => wanted.includes(e.type) && latest.current(e);
    listeners.add(l);
    return () => void listeners.delete(l);
  }, [key]);
}
