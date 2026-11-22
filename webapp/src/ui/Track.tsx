import type { CSSProperties } from "react";
import type { Status } from "../api";
import { named } from "../i18n";

const FULL: Status[] = ["paid", "in_queue", "assigned", "ready", "completed"];
const ENDED: Status[] = ["cancelled", "failed", "refunded"];

/** The order track: the line grows to the current step. Orders without an executor
 * (stock, fixed, manual) have two steps. A cancelled/failed/refunded order stops where it got
 * and ends with the status in the destructive colour. */
export function Track({ status, hasExecutor }: { status: Status; hasExecutor: boolean }) {
  const ended = ENDED.includes(status);
  let steps: string[];
  let at: number;
  if (ended) {
    const reached = status === "cancelled" ? "in_queue" : hasExecutor ? "ready" : "paid";
    steps = [...FULL.slice(0, FULL.indexOf(reached) + 1), status];
    at = steps.length - 1;
  } else {
    const full = hasExecutor || status === "in_queue" || status === "assigned" || status === "ready";
    steps = full ? FULL : ["paid", "completed"];
    at = Math.max(0, steps.indexOf(status));
  }
  const fill = ended ? (at - 1) / (steps.length - 1) : at / (steps.length - 1);
  const style = { "--n": steps.length, "--fill": fill } as CSSProperties;
  return (
    <div className="track" style={style}>
      <div className="track-line">
        <i />
      </div>
      <ol>
        {steps.map((step, i) => {
          const state =
            ended && i === at
              ? "end"
              : i < at || (status === "completed" && i === at)
                ? "done"
                : i === at
                  ? "now"
                  : "next";
          return (
            <li key={step} className={state} style={{ "--i": i } as CSSProperties}>
              <b />
              <span>{named("track", step)}</span>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
