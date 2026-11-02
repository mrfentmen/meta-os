// Meta Aegis — run the secret-hygiene count (AEGIS_SPEC.md, "Secret hygiene").
//
//   node aegis/run-secrets.mjs [root]
//
// Writes os-build/aegis/SECRETS.md and SECRETS.json. The JSON holds counts and locations --
// path, line, pattern -- and no matched text, because the artifact is committed to a public
// repository and a scan that republishes what it found is the leak wearing a badge.
import fs from "node:fs";
import path from "node:path";
import { scanTree, renderReport } from "./secrets.mjs";

const root = process.argv[2] ? path.resolve(process.argv[2]) : process.cwd();
const outDir = path.join(root, "os-build", "aegis");
const runId = "secrets-" + new Date().toISOString().replace(/[:.]/g, "-");

const result = scanTree(root);
fs.mkdirSync(outDir, { recursive: true });
fs.writeFileSync(path.join(outDir, "SECRETS.md"), renderReport(result, { runId }));
fs.writeFileSync(path.join(outDir, "SECRETS.json"), JSON.stringify({
  run: runId,
  ts: new Date().toISOString(),
  root: path.basename(root),
  scanned: result.scanned,
  skipped: result.skipped,
  counts: result.counts,
  byConfidence: result.byConfidence,
  locations: result.locations,
  allowlisted: result.allowlisted.length,
}, null, 2) + "\n");

const total = result.byConfidence.confirmed + result.byConfidence.review;
console.log("aegis secrets " + runId);
console.log("  files read   " + result.scanned);
console.log("  confirmed    " + result.byConfidence.confirmed);
console.log("  review       " + result.byConfidence.review);
console.log("  allowlisted  " + result.allowlisted.length);
console.log("  report       " + path.relative(process.cwd(), path.join(outDir, "SECRETS.md")));
process.exit(0);
