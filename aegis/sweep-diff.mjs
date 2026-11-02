// Aegis sweep diff (R12-003) — the MECHANICS PROOF, not a new vulnerability claim.
//
// Two findings snapshots in, one delta out. A finding's identity is its target plus its advisory
// title; the same advisory against two versions is two findings. An empty diff is a valid and
// expected result when the same tree is swept twice the same day.
import fs from "node:fs";
import path from "node:path";
import { readFindings } from "./findings.mjs";

export function diffFindings(before, after) {
  const key = (f) => (f.target || "") + "|" + f.title;
  const b = new Map(before.map((f) => [key(f), f]));
  const a = new Map(after.map((f) => [key(f), f]));
  const added = [...a.keys()].filter((k) => !b.has(k)).map((k) => a.get(k));
  const removed = [...b.keys()].filter((k) => !a.has(k)).map((k) => b.get(k));
  const unchanged = [...a.keys()].filter((k) => b.has(k)).map((k) => a.get(k));
  return { before: before.length, after: after.length, added, removed, unchanged };
}

export function renderDiff(d, { beforeFile, afterFile, runId } = {}) {
  const lines = [];
  lines.push("# Aegis sweep diff — mechanics proof");
  lines.push("");
  lines.push("Run `" + runId + "`. Before: `" + beforeFile + "` (" + d.before + " findings). After: `" + afterFile + "` (" + d.after + ").");
  lines.push("");
  lines.push("| delta | count |");
  lines.push("|---|---|");
  lines.push("| added | " + d.added.length + " |");
  lines.push("| removed | " + d.removed.length + " |");
  lines.push("| unchanged | " + d.unchanged.length + " |");
  lines.push("");
  if (!d.added.length && !d.removed.length) {
    lines.push("**Empty diff.** The machinery ran end to end and the two runs agreed. That is the expected");
    lines.push("result for the same tree swept twice the same day; it is not evidence that the tree is clean.");
  }
  if (d.added.length) {
    lines.push("## Added");
    lines.push("");
    for (const f of d.added) lines.push("- " + f.title + " (`" + (f.target || "no target") + "`)");
    lines.push("");
  }
  if (d.removed.length) {
    lines.push("## Removed");
    lines.push("");
    for (const f of d.removed) lines.push("- " + f.title + " (`" + (f.target || "no target") + "`)");
    lines.push("");
  }
  lines.push("## What this does not claim");
  lines.push("");
  lines.push("- A removed finding is not a fixed one: it may be a version bump, a changed source, or a");
  lines.push("  different query answer. The records say what was seen, not why it moved.");
  lines.push("");
  return lines.join("\n");
}

if (process.argv[1] && path.resolve(process.argv[1]) === path.resolve(new URL(import.meta.url).pathname)) {
  const [, , beforeFile, afterFile] = process.argv;
  if (!beforeFile || !afterFile) { console.error("usage: sweep-diff.mjs <before.jsonl> <after.jsonl>"); process.exit(2); }
  const runId = "sweep-diff-" + new Date().toISOString().replace(/[:.]/g, "-");
  const d = diffFindings(readFindings(beforeFile).findings, readFindings(afterFile).findings);
  const md = renderDiff(d, { beforeFile, afterFile, runId });
  const out = path.join(process.cwd(), "os-build", "aegis", "SWEEP_DIFF.md");
  fs.writeFileSync(out, md);
  fs.writeFileSync(out.replace(/\.md$/, ".json"), JSON.stringify({ run: runId, ...d }, null, 2) + "\n");
  console.log("sweep diff: before " + d.before + ", after " + d.after + ", added " + d.added.length + ", removed " + d.removed.length);
}
