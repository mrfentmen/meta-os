// Meta Aegis — run the pre-publish review (AEGIS_SPEC.md, wing 7).
//
//   node aegis/run-opsec.mjs [file ...]
//
// Default set: the submission's own copy — the demo script, the site copy, the README, and the
// checklist that describes the package. Writes os-build/aegis/OPSEC.md and appends findings.
import fs from "node:fs";
import path from "node:path";
import { scanFiles, findingsFrom, renderReport } from "./opsec.mjs";
import { appendFinding } from "./findings.mjs";

export const DEFAULT_MATERIALS = [
  "README.md",
  "os-build/DEMO_SCRIPT.md",
  "os-build/layer1/DEMO_30S.md",
  "os-build/SUBMISSION_CHECKLIST.md",
  "site/index.html",
];

const root = process.env.AEGIS_ROOT ? path.resolve(process.env.AEGIS_ROOT) : process.cwd();
const outDir = path.join(root, "os-build", "aegis");
const materials = process.argv.slice(2).length ? process.argv.slice(2) : DEFAULT_MATERIALS;
const runId = "opsec-" + new Date().toISOString().replace(/[:.]/g, "-");

const scan = scanFiles(materials, { root });
const findings = findingsFrom(scan, { runId }).map((f) => appendFinding(path.join(outDir, "findings.jsonl"), f));

fs.mkdirSync(outDir, { recursive: true });
fs.writeFileSync(path.join(outDir, "OPSEC.md"), renderReport(scan, findings, { runId, materials }));
console.log("aegis opsec " + runId);
console.log("  files read  " + scan.files.length + (scan.missing.length ? " (" + scan.missing.length + " missing)" : ""));
for (const [id, n] of Object.entries(scan.counts)) console.log("  " + id.padEnd(12) + " " + n);
console.log("  findings    " + findings.length);
console.log("  report      " + path.relative(process.cwd(), path.join(outDir, "OPSEC.md")));
process.exit(0);
