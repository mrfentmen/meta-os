// Run the KEV cross-check over Aegis findings (R12-002).
//   node aegis/run-kev.mjs [findings.jsonl] [kev.json]
// With no kev.json, fetches the public CISA feed (Pax's exception covers this sweep).
import fs from "node:fs";
import path from "node:path";
import { readFindings } from "./findings.mjs";
import { indexKev, crossCheck, renderKev, KEV_URL } from "./kev.mjs";

const root = process.cwd();
const findingsFile = process.argv[2] || path.join(root, "os-build", "aegis", "findings.jsonl");
const kevArg = process.argv[3] || process.env.AEGIS_KEV_JSON;
const runId = "kev-" + new Date().toISOString().replace(/[:.]/g, "-");

let doc;
if (kevArg) doc = JSON.parse(fs.readFileSync(kevArg, "utf8"));
else {
  const res = await fetch(KEV_URL, { headers: { "user-agent": "meta-aegis-kev/1" } });
  if (!res.ok) { console.error("kev: HTTP " + res.status); process.exit(3); }
  doc = await res.json();
}
const kev = indexKev(doc);
const { findings } = readFindings(findingsFile);
// KEV is a check on DEPENDENCY findings. The findings file also holds OSINT records (DNS/CT),
// which carry no package and no CVE; checking them would report "unchecked" noise as if the
// sweep had findings it did not have (R12-002). Sweep records are identified by the title shape
// `<advisory> affects <package> <version>` written by aegis/sweep.mjs.
const sweepFindings = findings.filter((f) => / affects /.test(f.title || ""));
const excluded = findings.length - sweepFindings.length;
const result = crossCheck(sweepFindings, kev);
result.excludedNonSweep = excluded;
fs.mkdirSync(path.join(root, "os-build", "aegis"), { recursive: true });
fs.writeFileSync(path.join(root, "os-build", "aegis", "KEV.md"), renderKev(result, { runId }));
fs.writeFileSync(path.join(root, "os-build", "aegis", "KEV.json"), JSON.stringify({
  run: runId, at: new Date().toISOString(), source: KEV_URL, findings: findingsFile,
  ...result,
}, null, 2) + "\n");
console.log("aegis kev " + runId);
console.log("  findings  " + result.checked);
console.log("  flagged   " + result.flagged);
console.log("  unchecked " + result.unchecked);
process.exit(0);
