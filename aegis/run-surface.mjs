// Meta Aegis — run the surface checks (AEGIS_SPEC.md, "Surface checks").
//
//   node aegis/run-surface.mjs [file ...]
//
// Default: the text that ships and the text that is published about it. Writes
// os-build/aegis/SURFACE.md. Codepoints and locations only, never the surrounding text.
import fs from "node:fs";
import path from "node:path";
import { scanFiles, renderReport } from "./surface.mjs";

export const DEFAULT_MATERIALS = [
  "README.md",
  "site/index.html",
  "os-build/DEMO_SCRIPT.md",
  "os-build/layer1/DEMO_30S.md",
  "os-build/SUBMISSION_CHECKLIST.md",
  "os-build/aegis/SWEEP.md",
  "os-build/aegis/OSINT.md",
];

const root = process.env.AEGIS_ROOT ? path.resolve(process.env.AEGIS_ROOT) : process.cwd();
const outDir = path.join(root, "os-build", "aegis");
const materials = process.argv.slice(2).length ? process.argv.slice(2) : DEFAULT_MATERIALS;
const runId = "surface-" + new Date().toISOString().replace(/[:.]/g, "-");

const scan = scanFiles(materials, { root });
fs.mkdirSync(outDir, { recursive: true });
fs.writeFileSync(path.join(outDir, "SURFACE.md"), renderReport(scan, { runId, materials }));
fs.writeFileSync(path.join(outDir, "SURFACE.json"), JSON.stringify({ run: runId, ts: new Date().toISOString(), files: scan.files, missing: scan.missing, counts: scan.counts, hits: scan.hits }, null, 2) + "\n");

console.log("aegis surface " + runId);
console.log("  files read  " + scan.files.length + (scan.missing.length ? " (" + scan.missing.length + " missing)" : ""));
for (const [k, v] of Object.entries(scan.counts)) if (v) console.log("  " + k.padEnd(20) + v);
console.log("  hits        " + scan.hits.length);
console.log("  report      " + path.relative(process.cwd(), path.join(outDir, "SURFACE.md")));
process.exit(0);
