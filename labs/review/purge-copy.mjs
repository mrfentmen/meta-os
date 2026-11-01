#!/usr/bin/env node
// labs/review/purge-copy.mjs — NC-075: purge false positives on a COPY.
// usage: node labs/review/purge-copy.mjs <in.jsonl> <out.jsonl> <id...>
// Marks each id false-positive, empties its evidence with a purge receipt.
// Prints before/after byte counts; exits nonzero if reconstruct finds gaps.
import { readFileSync, writeFileSync } from "node:fs";

const [src, dst, ...ids] = process.argv.slice(2);
if (!src || !dst || !ids.length) {
  console.error("usage: node purge-copy.mjs <in.jsonl> <out.jsonl> <id...>");
  process.exit(2);
}
const before = readFileSync(src, "utf8");
const recs = before.split("\n").filter((l) => l.trim()).map(JSON.parse);
let purged = 0;
for (const r of recs) {
  if (ids.includes(r.incident.id)) {
    r.incident.false_positive = true;
    r.evidence = { frames: [], face_boxes: [], purged: true, purge_reason: "false positive close" };
    purged++;
  }
}
const after = recs.map((r) => JSON.stringify(r)).join("\n") + "\n";
writeFileSync(dst, after);
// reconstruct check: every input id present exactly once, order kept.
const idsBefore = recs.map((r) => r.incident.id);
const idsAfter = after.split("\n").filter((l) => l.trim()).map((l) => JSON.parse(l).incident.id);
const gaps = idsBefore.length !== idsAfter.length || idsBefore.some((id, i) => id !== idsAfter[i]);
console.log(`purged=${purged} bytes_before=${before.length} bytes_after=${after.length} gaps=${gaps}`);
if (gaps) process.exit(1);
