// Meta Aegis — R12-020, false-positive drill.
//
// A known-clean manifest set is swept. The source's clean answer is supplied by a stub client
// with the exact text the real source returns, so this drills the sweep and report for false
// positives, not OSV's data. If the sweep reports a finding on clean input, the drill fails and
// files a finding against the sweep itself.
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { runSweep, renderReport } from "./sweep.mjs";
import { appendFinding } from "./findings.mjs";
import { Ledger } from "../agents/runtime.mjs";

const root = process.cwd();
const outDir = path.join(root, "os-build", "aegis");
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "aegis-fp-"));
const runId = "fp-drill-" + new Date().toISOString().replace(/[:.]/g, "-");

// Three packages with no known advisories at these versions, pinned exactly so the manifest is
// reproducible. The stub answers clean for whatever it is asked; the count is asserted below.
const CLEAN = [
  ["left-pad", "1.3.0"],
  ["is-number", "7.0.0"],
  ["ansi-regex", "5.0.1"],
];
const packages = {};
for (const [name, version] of CLEAN) packages["node_modules/" + name] = { version };
packages[""] = { name: "aegis-fp-drill", version: "1.0.0" };
fs.writeFileSync(path.join(tmp, "package-lock.json"), JSON.stringify({
  name: "aegis-fp-drill", version: "1.0.0", lockfileVersion: 3, requires: true, packages,
}, null, 2));

let asked = 0;
const client = {
  async callTool(name, args) {
    if (name !== "scan_packages") throw new Error("unexpected tool " + name);
    asked = args.packages.length;
    return { text: "No known vulnerabilities found across " + asked + " package(s)." };
  },
  close() {},
};

const result = await runSweep({
  root: tmp, outDir: path.join(tmp, "out"), client, runId,
  sourceLabel: "stub source: exact clean-answer text (false-positive drill)",
  sourceServer: "aegis-fp-drill stub",
});
const clean = result.status === "ran" && result.findings.length === 0 && result.checked === CLEAN.length && asked === CLEAN.length;
fs.writeFileSync(path.join(tmp, "out", "SWEEP.md"), renderReport(result, { runId }));

if (!clean) {
  appendFinding(path.join(outDir, "findings.jsonl"), {
    severity: "high",
    title: "Aegis sweep reported dirt on a known-clean manifest set",
    evidence: "status=" + result.status + " findings=" + result.findings.length +
      " checked=" + result.checked + " asked=" + asked + "; expected 0 findings and " + CLEAN.length + " checked",
    source: "aegis/fp-drill.mjs",
    run: runId,
    target: "false-positive drill",
  });
}

const receipt = {
  task: "R12-020",
  run: runId,
  at: new Date().toISOString(),
  ok: clean,
  manifests: 1,
  packages: CLEAN.map(([name, version]) => name + "@" + version),
  checked: result.checked,
  findings: result.findings.length,
  status: result.status,
  source: "stub client, exact clean-answer text; this is a sweep/report drill, not an OSV result",
  failure: clean ? null : "the sweep did not report the clean set clean; a finding was filed against the sweep",
};
fs.mkdirSync(path.join(root, "os-build", "layer1", "r12"), { recursive: true });
fs.writeFileSync(path.join(root, "os-build", "layer1", "r12", "FALSE_POSITIVE_DRILL.json"),
  JSON.stringify(receipt, null, 2) + "\n");
fs.writeFileSync(path.join(outDir, "FALSE_POSITIVE_DRILL.md"),
  "# Aegis false-positive drill\n\n" +
  "Run `" + runId + "`. A manifest with three pinned clean packages was swept with a stub source\n" +
  "returning the source's exact clean-answer text.\n\n" +
  "| item | value |\n|---|---|\n" +
  "| status | **" + result.status + "** |\n" +
  "| packages queried | " + result.checked + " |\n" +
  "| findings | **" + result.findings.length + "** |\n" +
  "| verdict | **" + (clean ? "CLEAN, as expected" : "FALSE POSITIVE — finding filed against the sweep") + "** |\n\n" +
  "This drills the sweep and the report for false positives. It is not a claim about OSV's data:\n" +
  "the transport was a stub, and the receipt says so.\n");
new Ledger(path.join(outDir, "runs.jsonl")).add(runId, "false-positive-drill", {
  ok: clean, checked: result.checked, findings: result.findings.length,
});
console.log("fp drill: " + (clean ? "CLEAN" : "FALSE POSITIVE") + " — checked " + result.checked + ", findings " + result.findings.length);
process.exit(clean ? 0 : 1);
