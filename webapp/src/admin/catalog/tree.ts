import type { AdminCategory } from "../../api";
import { pick } from "../kit";

export const childrenOf = (cats: AdminCategory[], parent: number | null) =>
  cats.filter((c) => c.parent_id === parent).sort((a, b) => a.position - b.position || a.id - b.id);

/** The tree as a flat select list, indented by depth; `exclude` drops a category with its subtree. */
export function categoryOptions(cats: AdminCategory[], exclude?: number): [string, string][] {
  const out: [string, string][] = [];
  const walk = (parent: number | null, depth: number) => {
    for (const c of childrenOf(cats, parent)) {
      if (c.id === exclude) continue;
      out.push([String(c.id), "   ".repeat(depth) + pick(c.title)]);
      walk(c.id, depth + 1);
    }
  };
  walk(null, 0);
  return out;
}

/** From the root down to `id`. */
export function pathTo(cats: AdminCategory[], id: number): AdminCategory[] {
  const path: AdminCategory[] = [];
  for (let c = cats.find((x) => x.id === id); c; c = cats.find((x) => x.id === c?.parent_id)) path.unshift(c);
  return path;
}
