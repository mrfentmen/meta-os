#!/usr/bin/env node
// labs/review/tier-counter.mjs — usage:
//   node labs/review/tier-counter.mjs <records.jsonl>
// Prints counts by tier (yellow, red, none, other). Exit 0 always;
// the numbers are the answer. Sample data carries exactly 3 yellow + 2 red.
import { readFileSync } from "node:fs";

const file = process.argv[2];
if (!file) {
  console.error("usage: node tier-counter.mjs <records.jsonl>");
  process.exit(2);
}
const counts = { yellow: 0, red: 0, none: 0, other: 0 };
let n = 0;
for (const line of readFileSync(file, "utf8").split("\n")) {
  const t = line.trim();
  if (!t) continue;
  n++;
  const tier = ((JSON.parse(t).incident || {}).tier || "none").toLowerCase();
  if (tier === "yellow") counts.yellow++;
  else if (tier === "red") counts.red++;
  else if (tier === "none") counts.none++;
  else counts.other++;
}
console.log(`records: ${n} yellow: ${counts.yellow} red: ${counts.red} none: ${counts.none} other: ${counts.other}`);
