#!/usr/bin/env node
// CB-097 — count secret-shaped strings in a log. Counts only; no value
// is ever printed.
import fs from "node:fs";

const PATTERNS = [
  { kind: "openai", re: /\bsk-[A-Za-z0-9_-]{20,}\b/g },
  { kind: "github", re: /\bghp_[A-Za-z0-9]{30,}\b/g },
  { kind: "aws", re: /\bAKIA[0-9A-Z]{16}\b/g },
  { kind: "assigned", re: /(?:api[_-]?key|secret)\s*[:=]\s*["']?[A-Za-z0-9._-]{16,}/gi },
];

export function countSecrets(text) {
  const byKind = {};
  let total = 0;
  for (const { kind, re } of PATTERNS) {
    const hits = text.match(re) || [];
    byKind[kind] = hits.length;
    total += hits.length;
  }
  return { total, byKind };
}

export function main(argv) {
  if (!argv[0]) { console.error("usage: redact_check.mjs <log>"); process.exitCode = 2; return; }
  const result = countSecrets(fs.readFileSync(argv[0], "utf8"));
  console.log("secret-shaped values: " + result.total);
  for (const [kind, count] of Object.entries(result.byKind)) console.log("  " + kind + ": " + count);
  console.log("counts only: no value printed");
}

if (process.argv[1] && import.meta.url.endsWith(process.argv[1].replace(/\\/g, "/"))) main(process.argv.slice(2));
