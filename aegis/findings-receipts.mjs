// Meta Aegis — R12-016, sweep findings to append-only ledger receipts.
//
// Every dependency finding becomes one receipt: severity, source route, timestamp, run, target.
// A run that found nothing still writes a batch receipt, because "checked and found zero" is a
// fact the ledger should hold, and silence is indistinguishable from "never ran".
//
// Receipts are append-only. Rerunning the same batch is idempotent by receipt hash, not by
// rewriting: an existing receipt is skipped, never edited.
import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { readFindings, summarize } from "./findings.mjs";
import { Ledger } from "../agents/runtime.mjs";

const root = process.cwd();
const outDir = path.join(root, "os-build", "aegis");
const findingsFile = process.argv[2] || path.join(outDir, "findings.jsonl");
const ledgerFile = path.join(outDir, "findings-ledger.jsonl");
const runId = "findings-" + new Date().toISOString().replace(/[:.]/g, "-");

const { findings, torn } = readFindings(findingsFile);
const sweepFindings = findings.filter((f) => / affects /.test(f.title || ""));
const hash = (f) => crypto.createHash("sha256")
  .update([f.title, f.run, f.target || "", f.severity].join("|")).digest("hex").slice(0, 20);

const existing = new Set();
if (fs.existsSync(ledgerFile)) {
  for (const line of fs.readFileSync(ledgerFile, "utf8").split("\n")) {
    if (!line) continue;
    try { const r = JSON.parse(line); if (r.receipt) existing.add(r.receipt); } catch { /* torn: skip */ }
  }
}

const written = [];
for (const f of sweepFindings) {
  const receipt = hash(f);
  if (existing.has(receipt)) continue;
  const rec = {
    v: 1,
    at: new Date().toISOString(),
    receipt,
    kind: "finding",
    severity: f.severity,
    source: f.source,
    sweepRun: f.run,
    target: f.target || null,
    title: f.title,
  };
  fs.appendFileSync(ledgerFile, JSON.stringify(rec) + "\n");
  written.push(receipt);
}
const batch = {
  v: 1,
  at: new Date().toISOString(),
  receipt: crypto.createHash("sha256").update(runId).digest("hex").slice(0, 20),
  kind: "batch",
  run: runId,
  findingsFile: path.relative(root, findingsFile),
  sweepFindings: sweepFindings.length,
  receiptsWritten: written.length,
  alreadyPresent: sweepFindings.length - written.length,
  nonSweepExcluded: findings.length - sweepFindings.length,
  tornLinesSkipped: torn,
  severity: summarize(sweepFindings).bySeverity,
  note: "append-only receipts; a zero-finding batch is recorded, not omitted",
};
fs.appendFileSync(ledgerFile, JSON.stringify(batch) + "\n");

const totalReceipts = fs.readFileSync(ledgerFile, "utf8").split("\n").filter(Boolean).length;
fs.writeFileSync(path.join(outDir, "FINDINGS_LEDGER.md"),
  "# Aegis findings ledger — " + new Date().toISOString().slice(0, 10) + "\n\n" +
  "Append-only receipts from `aegis/findings-receipts.mjs`. Every dependency finding in\n" +
  "`" + path.relative(root, findingsFile) + "` becomes one receipt with severity, source route,\n" +
  "timestamp, sweep run and target. A batch receipt is written even when the count is zero.\n\n" +
  "| item | count |\n|---|---|\n" +
  "| sweep findings in source | " + sweepFindings.length + " |\n" +
  "| receipts written this run | " + written.length + " |\n" +
  "| already present (skipped, not rewritten) | " + (sweepFindings.length - written.length) + " |\n" +
  "| non-sweep records excluded | " + (findings.length - sweepFindings.length) + " |\n" +
  "| ledger lines now | " + totalReceipts + " |\n\n" +
  (sweepFindings.length ? "" : "**Zero dependency findings.** The batch receipt records that the sweep ran and\n" +
    "returned nothing; it is not an empty file and not a claim about unexamined references.\n"));

new Ledger(path.join(outDir, "runs.jsonl")).add(runId, "findings-receipts", {
  sweepFindings: sweepFindings.length, written: written.length, ledgerLines: totalReceipts,
});
console.log("findings receipts " + runId);
console.log("  sweep findings " + sweepFindings.length + ", written " + written.length + ", excluded " + (findings.length - sweepFindings.length));
