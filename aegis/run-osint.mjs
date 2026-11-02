// Meta Aegis — run OSINT v1 (AEGIS_SPEC.md, wing 6).
//
//   node aegis/run-osint.mjs [domain ...]
//
// Defaults to the four domains the boss named. Writes os-build/aegis/OSINT.md and appends any
// findings to os-build/aegis/findings.jsonl. Counts and locations only: no name, address, or
// record value is written to either artifact.
import fs from "node:fs";
import path from "node:path";
import { runOsint, renderReport, DEFAULT_DOMAINS } from "./osint.mjs";

const root = process.env.AEGIS_ROOT ? path.resolve(process.env.AEGIS_ROOT) : process.cwd();
const outDir = path.join(root, "os-build", "aegis");
const domains = process.argv.slice(2).length ? process.argv.slice(2) : DEFAULT_DOMAINS;
const runId = "osint-" + new Date().toISOString().replace(/[:.]/g, "-");

const result = await runOsint({ domains, outDir, runId });
fs.mkdirSync(outDir, { recursive: true });
fs.writeFileSync(path.join(outDir, "OSINT.md"), renderReport(result, { runId, domains }));
fs.writeFileSync(path.join(outDir, "OSINT.json"), JSON.stringify({
  run: runId, ts: new Date().toISOString(), status: result.status, domains, results: result.results,
}, null, 2) + "\n");

console.log("aegis osint " + runId);
console.log("  status    " + result.status);
for (const r of result.results) {
  console.log("  " + r.domain.padEnd(30) + " ct=" + (r.ct.ok ? "ok" : "unavailable") +
    " certs=" + r.ct.certificates + " names=" + r.ct.distinctNames +
    " spf=" + (r.dns.spf ? "yes" : "no") + " dmarc=" + (r.dns.dmarc ? "yes" : "no"));
}
console.log("  findings  " + result.findings.length);
console.log("  report    " + path.relative(process.cwd(), path.join(outDir, "OSINT.md")));
process.exit(0);
