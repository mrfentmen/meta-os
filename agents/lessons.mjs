// The Graft — the boss's rule (2026-10-26): "one agent learns, the
// whole crew levels up." A FEATURE of the agent layer, not a product.
// Lessons are append-only, shared by every agent, and the newest
// ones ride into every brief at spawn — an agent opens its eyes
// already knowing what the crew learned without it.
import fs from "node:fs";

export function lessonsFile(root) { return root + "/lessons.jsonl"; }

export function teach(root, agent, text) {
  const line = JSON.stringify({ ts: new Date().toISOString(), agent, text }) + "\n";
  fs.appendFileSync(lessonsFile(root), line);
  return line;
}

export function lessons(root, limit = 20) {
  try {
    const all = fs.readFileSync(lessonsFile(root), "utf8").split("\n").filter(Boolean).map((l) => JSON.parse(l));
    return all.slice(-limit);
  } catch { return []; }
}
