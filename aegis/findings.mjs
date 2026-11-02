// Meta Aegis — D2, the findings record (AEGIS_SPEC.md, "Report" + "Proof obligations").
//
// Append-only JSONL. A finding is a claim with a source and a run: severity, evidence,
// source, run. There is no update and no delete in this module — a record that can be
// edited after the fact is not evidence, and the sizing rule (quiet note vs full alarm)
// depends on the record being the same one the sweep wrote.
//
// Same torn-line recovery as the run ledger (agents/runtime.mjs): one separator byte before
// an append, and a reader that skips what it cannot parse. A crash leaves a record missing,
// never a whole file unreadable. Skipped lines are counted, not repaired.
import fs from "node:fs";
import path from "node:path";

export const SEVERITIES = ["info", "low", "medium", "high", "critical"];

const LIMITS = { title: 200, evidence: 4000, source: 500, run: 200, target: 500 };

export class FindingError extends Error {}

function requireText(finding, key, max) {
  const v = finding[key];
  if (typeof v !== "string" || v.trim() === "") {
    throw new FindingError("finding: " + key + " is required (non-empty string)");
  }
  const t = v.trim();
  if (t.length > max) throw new FindingError("finding: " + key + " exceeds " + max + " chars");
  return t;
}

function endsWithNewline(file) {
  try {
    const st = fs.statSync(file);
    if (!st.size) return true;
    const fd = fs.openSync(file, "r");
    const b = Buffer.alloc(1);
    fs.readSync(fd, b, 0, 1, st.size - 1);
    fs.closeSync(fd);
    return b[0] === 0x0a;
  } catch { return true; }   // no file yet: nothing to separate from
}

export function appendFinding(file, finding) {
  if (!finding || typeof finding !== "object") throw new FindingError("finding: expected an object");
  if (!SEVERITIES.includes(finding.severity)) {
    throw new FindingError("finding: severity must be one of " + SEVERITIES.join(", "));
  }
  // ts is set here, not accepted from the caller: a record the writer can backdate is a
  // record nobody can order.
  const rec = {
    ts: new Date().toISOString(),
    v: 1,
    severity: finding.severity,
    title: requireText(finding, "title", LIMITS.title),
    evidence: requireText(finding, "evidence", LIMITS.evidence),
    source: requireText(finding, "source", LIMITS.source),
    run: requireText(finding, "run", LIMITS.run),
  };
  if (finding.target != null) rec.target = requireText(finding, "target", LIMITS.target);

  fs.mkdirSync(path.dirname(file), { recursive: true });
  const sep = endsWithNewline(file) ? "" : "\n";
  fs.appendFileSync(file, sep + JSON.stringify(rec) + "\n");
  return rec;
}

export function readFindings(file) {
  if (!fs.existsSync(file)) return { findings: [], torn: 0 };
  const findings = [];
  let torn = 0;
  for (const line of fs.readFileSync(file, "utf8").split("\n")) {
    if (!line) continue;
    try { findings.push(JSON.parse(line)); } catch { torn += 1; }
  }
  return { findings, torn };
}

export function summarize(findings) {
  const bySeverity = {};
  for (const s of SEVERITIES) bySeverity[s] = 0;
  for (const f of findings) if (bySeverity[f.severity] != null) bySeverity[f.severity] += 1;
  return { total: findings.length, bySeverity };
}
