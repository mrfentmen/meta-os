// Meta Aegis — R12-018, OPSEC checklist over the submission materials.
//
// Pass/fail per item, per file. A failure is also appended to findings.jsonl with a location and
// a count, never the matched text. A binary (screenshot) is not text-scanned and is recorded as
// UNCHECKED, not as a pass.
import fs from "node:fs";
import path from "node:path";
import { appendFinding, readFindings } from "./findings.mjs";
import { Ledger } from "../agents/runtime.mjs";

const root = process.cwd();
const outDir = path.join(root, "os-build", "aegis");
const runId = "opsec-" + new Date().toISOString().replace(/[:.]/g, "-");

const TEXT_MATERIALS = [
  "README.md",
  "os-build/layer1/DEMO_30S.md",
  "os-build/layer1/DEMO_FACTS.md",
  "os-build/SCOREBOARD.md",
];
const present = TEXT_MATERIALS.filter((f) => fs.existsSync(path.join(root, f)));
const missing = TEXT_MATERIALS.filter((f) => !fs.existsSync(path.join(root, f)));

const screenshots = [];
(function walk(dir, depth) {
  if (depth > 2) return;
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    if (e.name.startsWith(".") || e.name === "node_modules") continue;
    const p = path.join(dir, e.name);
    if (e.isDirectory()) walk(p, depth + 1);
    else if (/\.(png|jpe?g|webp)$/i.test(e.name)) screenshots.push(path.relative(root, p));
  }
})(root, 0);

const CHECKS = [
  { id: "no-private-key", severity: "critical", re: /-----BEGIN (?:RSA |EC |OPENSSH |PGP )?PRIVATE KEY-----/ },
  { id: "no-cloud-token", severity: "high", re: /\b(?:AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9]{36,}|xox[baprs]-[A-Za-z0-9-]{10,}|sk-[A-Za-z0-9_-]{20,})\b/ },
  { id: "no-absolute-home-path", severity: "medium", re: /\/Users\/[A-Za-z0-9._-]+/ },
  { id: "no-email-address", severity: "low", re: /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b/ },
  { id: "no-env-assignment", severity: "high", re: /^\s*[A-Z0-9_]*(?:KEY|TOKEN|SECRET|PASSWORD)\s*=\s*\S{8,}/m },
];

const rows = [];
const findings = [];
for (const rel of present) {
  const text = fs.readFileSync(path.join(root, rel), "utf8");
  for (const check of CHECKS) {
    const lines = text.split("\n");
    const hits = [];
    lines.forEach((line, i) => { if (check.re.test(line)) hits.push(i + 1); });
    rows.push({ file: rel, check: check.id, state: hits.length ? "FAIL" : "PASS", hits: hits.length, lines: hits.slice(0, 8) });
    if (hits.length) {
      findings.push({ rel, check, hits });
    }
  }
}
for (const shot of screenshots) {
  rows.push({ file: shot, check: "screenshot-content", state: "UNCHECKED", hits: 0, lines: [], why: "binary; no OCR in this check" });
}

let ledgerRun = null;
if (findings.length) {
  ledgerRun = runId;
  for (const f of findings) {
    appendFinding(path.join(outDir, "findings.jsonl"), {
      severity: f.check.severity,
      title: "OPSEC " + f.check.id + " in " + f.rel,
      evidence: "checklist check " + f.check.id + " failed in " + f.rel + " on " + f.hits.length +
        " line(s): " + f.hits.slice(0, 8).join(", ") + " (values not recorded)",
      source: "aegis/opsec-r12.mjs checklist",
      run: runId,
      target: f.rel,
    });
  }
}

const fails = rows.filter((r) => r.state === "FAIL");
const passes = rows.filter((r) => r.state === "PASS");
const unchecked = rows.filter((r) => r.state === "UNCHECKED");
const md = [];
md.push("# Aegis OPSEC checklist — hackathon submission materials");
md.push("");
md.push("Run `" + runId + "`, " + new Date().toISOString() + ". Checks are text-pattern checks over the");
md.push("named materials; a matched value is never written. Screenshots are binary and are listed as");
md.push("UNCHECKED — no OCR was run, so nothing is claimed about their content.");
md.push("");
md.push("| item | count |");
md.push("|---|---|");
md.push("| materials checked | " + present.length + " |");
md.push("| checks passed | " + passes.length + " |");
md.push("| checks failed | " + fails.length + " |");
md.push("| screenshots unchecked | " + unchecked.length + " |");
md.push("| materials missing | " + missing.length + " |");
md.push("");
md.push("| file | check | state | hits | lines |");
md.push("|---|---|---|---|---|");
for (const r of rows) {
  md.push("| `" + r.file + "` | " + r.check + " | **" + r.state + "** | " + r.hits + " | " + (r.lines.join(", ") || "—") + " |");
}
md.push("");
if (missing.length) {
  md.push("Missing named materials (not silently skipped): " + missing.map((m) => "`" + m + "`").join(", ") + ".");
  md.push("");
}
md.push("## What this checklist does not do");
md.push("");
md.push("- It does not read screenshot pixels, PDFs, or images.");
md.push("- It does not prove a secret is absent: it proves these patterns did not match these files.");
md.push("- It does not review git history (that is `HISTORY_SCAN.md`).");
fs.writeFileSync(path.join(outDir, "OPSEC_R12.md"), md.join("\n") + "\n");

new Ledger(path.join(outDir, "runs.jsonl")).add(runId, "opsec-checklist", {
  materials: present.length, passed: passes.length, failed: fails.length,
  screenshotsUnchecked: unchecked.length, findingsFiled: findings.length,
});
console.log("opsec: " + passes.length + " pass, " + fails.length + " fail, " + unchecked.length + " screenshot(s) unchecked");
for (const f of fails) console.log("  FAIL " + f.file + " " + f.check + " lines " + f.lines.join(","));
