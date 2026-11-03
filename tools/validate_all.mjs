// CB-051..060 — one validator for the nine record shapes in
// os-build/schemas/records.schema.json. Counts only: the CLI prints how many
// records passed per kind and never echoes a record (findings can carry host
// names and incident text).
import fs from "node:fs";
import path from "node:path";
import url from "node:url";
import { validateEntry } from "../agents/runtime.mjs";

const ROOT = path.resolve(path.dirname(url.fileURLToPath(import.meta.url)), "..");
export const SCHEMA_FILE = path.join(ROOT, "os-build/schemas/records.schema.json");
export const SCHEMAS = JSON.parse(fs.readFileSync(SCHEMA_FILE, "utf8"));
export const KINDS = Object.keys(SCHEMAS.$defs);

const ISO_DATE = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$/;
const HEX64 = /^[a-f0-9]{64}$/i;
const SECRET_VALUE = /\b(?:sk-[A-Za-z0-9_-]{20,}|ghp_[A-Za-z0-9]{30,}|AKIA[0-9A-Z]{16}|xox[baprs]-[A-Za-z0-9-]{10,})\b|(?:api[_-]?key|access[_-]?token|secret)\s*[:=]\s*["']?[A-Za-z0-9._-]{16,}/i;
const PHASES = ["problem", "literature", "hypotheses", "compute", "critique", "verification", "wetlab", "publication", "sealing", "sealed"];
const GATES = ["open", "human-gated", "closed"];
const SEVERITIES = ["info", "low", "medium", "high", "critical"];

const isObj = (v) => v !== null && typeof v === "object" && !Array.isArray(v);
const nonEmpty = (v) => typeof v === "string" && v.trim() !== "";

function validateIncident(rec, errors) {
  if (!isObj(rec) || !isObj(rec.incident)) {
    errors.push("incident: missing incident object");
    return;
  }
  const i = rec.incident;
  for (const field of ["id", "product", "category", "camera", "description", "identity"]) {
    if (!nonEmpty(i[field])) errors.push("incident." + field + ": expected a non-empty string");
  }
  if (typeof i.simulated !== "boolean") errors.push("incident.simulated: expected a boolean");
  if (!["red", "yellow", "green"].includes(i.tier)) errors.push("incident.tier: expected red, yellow or green");
  if (!ISO_DATE.test(i.timestamp || "")) errors.push("incident.timestamp: expected an ISO-8601 timestamp");
  if (i.visible_marks != null && !(Array.isArray(i.visible_marks) && i.visible_marks.every((x) => typeof x === "string"))) {
    errors.push("incident.visible_marks: expected an array of strings");
  }
  if (!isObj(rec.evidence)) errors.push("incident: missing evidence object");
  else if (!Array.isArray(rec.evidence.frames)) errors.push("incident.evidence.frames: expected an array");
}

function validateCycle(rec, errors) {
  if (!isObj(rec)) return errors.push("cycle: expected an object");
  if (!nonEmpty(rec.cycle_id)) errors.push("cycle.cycle_id: expected a non-empty string");
  if (!PHASES.includes(rec.phase)) errors.push("cycle.phase: expected one of " + PHASES.join(", "));
  if (!GATES.includes(rec.gate_state)) errors.push("cycle.gate_state: expected one of " + GATES.join(", "));
  if (!Array.isArray(rec.history) || rec.history.length === 0 || !rec.history.every((h) => HEX64.test(h))) {
    errors.push("cycle.history: expected a non-empty array of 64-char hashes");
  }
  if (!isObj(rec.inputs)) errors.push("cycle.inputs: expected an object");
  if (!isObj(rec.outputs)) errors.push("cycle.outputs: expected an object");
}

function findSecret(value, at = "") {
  if (typeof value === "string") return SECRET_VALUE.test(value) ? at || "(root)" : null;
  if (Array.isArray(value)) {
    for (let i = 0; i < value.length; i++) {
      const hit = findSecret(value[i], at + "[" + i + "]");
      if (hit) return hit;
    }
    return null;
  }
  if (isObj(value)) {
    for (const [key, inner] of Object.entries(value)) {
      const hit = findSecret(inner, at ? at + "." + key : key);
      if (hit) return hit;
    }
  }
  return null;
}

function validateAegis(rec, errors) {
  if (!isObj(rec)) return errors.push("aegis-finding: expected an object");
  for (const field of ["title", "evidence", "source", "run"]) {
    if (!nonEmpty(rec[field])) errors.push("aegis-finding." + field + ": expected a non-empty string");
  }
  if (!ISO_DATE.test(rec.ts || "")) errors.push("aegis-finding.ts: expected an ISO-8601 timestamp");
  if (!SEVERITIES.includes(rec.severity)) errors.push("aegis-finding.severity: expected one of " + SEVERITIES.join(", "));
  if (rec.v != null && (!Number.isInteger(rec.v) || rec.v < 1)) errors.push("aegis-finding.v: expected an integer >= 1");
  if (rec.target != null && !nonEmpty(rec.target)) errors.push("aegis-finding.target: expected a non-empty string");
  const secretAt = findSecret(rec);
  if (secretAt) errors.push("aegis-finding: secret-shaped value in " + secretAt);
}

function validateReceipt(rec, errors) {
  if (!isObj(rec)) return errors.push("model-receipt: expected an object");
  for (const field of ["kind", "model", "surface"]) {
    if (!nonEmpty(rec[field])) errors.push("model-receipt." + field + ": expected a non-empty string");
  }
  if (!ISO_DATE.test(rec.ts || "")) errors.push("model-receipt.ts: expected an ISO-8601 timestamp");
  if (!isObj(rec.usage)) errors.push("model-receipt.usage: expected an object");
  else if (!Number.isInteger(rec.usage.total_tokens) || rec.usage.total_tokens < 0) {
    errors.push("model-receipt.usage.total_tokens: expected an integer >= 0");
  }
  if (typeof rec.latency_ms !== "number" || !Number.isFinite(rec.latency_ms) || rec.latency_ms < 0) {
    errors.push("model-receipt.latency_ms: expected a number >= 0");
  }
  if (rec.est_cost_usd !== null && (typeof rec.est_cost_usd !== "number" || rec.est_cost_usd < 0)) {
    errors.push("model-receipt.est_cost_usd: expected null or a number >= 0");
  }
}

function validateRegistry(rec, errors) {
  try {
    validateEntry(rec);
  } catch (err) {
    errors.push(err.message);
  }
  if (isObj(rec) && isObj(rec.budget) && rec.budget.maxWallMs != null && !(rec.budget.maxWallMs > 0)) {
    errors.push("registry-entry.budget.maxWallMs: expected a number > 0");
  }
}

function validateBootRow(rec, errors) {
  if (!isObj(rec)) return errors.push("boot-log-index-row: expected an object");
  if (!nonEmpty(rec.file)) errors.push("boot-log-index-row.file: expected a non-empty string");
  if (!Number.isInteger(rec.lines) || rec.lines < 0) errors.push("boot-log-index-row.lines: expected an integer >= 0");
  if (typeof rec.first_marker !== "string") errors.push("boot-log-index-row.first_marker: expected a string");
}

function validateProofRow(rec, errors) {
  if (!isObj(rec)) return errors.push("proof-ledger-row: expected an object");
  for (const field of ["program", "command", "evidence"]) {
    if (!nonEmpty(rec[field])) errors.push("proof-ledger-row." + field + ": expected a non-empty string");
  }
  if (!Number.isInteger(rec.count) || rec.count < 0) errors.push("proof-ledger-row.count: expected an integer >= 0");
}

function validateWatchTarget(rec, errors) {
  if (!isObj(rec)) return errors.push("watch-target: expected an object");
  if (rec.type !== "file") errors.push("watch-target.type: expected file");
  if (!nonEmpty(rec.path)) errors.push("watch-target.path: expected a non-empty string");
}

function validateBaton(rec, errors) {
  if (!isObj(rec)) return errors.push("baton-handoff: expected an object");
  if (!nonEmpty(rec.jobId)) errors.push("baton-handoff.jobId: expected a non-empty string");
  if (!Array.isArray(rec.authors) || rec.authors.length === 0 || !rec.authors.every(nonEmpty)) {
    errors.push("baton-handoff.authors: expected a non-empty array of names");
  }
  if (rec.state != null && typeof rec.state !== "string") errors.push("baton-handoff.state: expected a string");
}

const VALIDATORS = {
  incident: validateIncident,
  cycle: validateCycle,
  "aegis-finding": validateAegis,
  "model-receipt": validateReceipt,
  "registry-entry": validateRegistry,
  "boot-log-index-row": validateBootRow,
  "proof-ledger-row": validateProofRow,
  "watch-target": validateWatchTarget,
  "baton-handoff": validateBaton,
};

export function validate(kind, rec) {
  const fn = VALIDATORS[kind];
  if (!fn) return { ok: false, errors: ["unknown record kind " + kind] };
  const errors = [];
  fn(rec, errors);
  return { ok: errors.length === 0, errors };
}

export function parseBootIndex(markdown) {
  const rows = [];
  for (const line of markdown.split(/\r?\n/)) {
    if (!line.startsWith("|")) continue;
    const cells = line.split("|").slice(1, -1).map((s) => s.trim());
    if (cells.length < 4) continue;
    const lines = Number(cells[1].replace(/,/g, ""));
    if (!Number.isInteger(lines) || lines < 0) continue;
    const file = cells[0].replace(/`/g, "").trim();
    if (!file || file.toLowerCase() === "file") continue;
    rows.push({ file, lines, first_marker: cells[2] });
  }
  return rows;
}

export function parseProofLedger(markdown) {
  const rows = [];
  for (const line of markdown.split(/\r?\n/)) {
    if (!line.startsWith("|")) continue;
    const cells = line.split("|").slice(1, -1).map((s) => s.trim());
    if (cells.length !== 6 || !/^\d+$/.test(cells[0])) continue;
    const countMatch = cells[3].match(/\d[\d,]*/);
    rows.push({
      program: cells[1],
      command: cells[2].replace(/`/g, ""),
      count: countMatch ? Number(countMatch[0].replace(/,/g, "")) : 0,
      evidence: cells[5].replace(/`/g, ""),
    });
  }
  return rows;
}

export function readJsonl(file) {
  const records = [];
  let skipped = 0;
  if (!fs.existsSync(file)) return { records, skipped };
  for (const line of fs.readFileSync(file, "utf8").split("\n")) {
    if (!line.trim()) continue;
    try { records.push(JSON.parse(line)); } catch { skipped++; }
  }
  return { records, skipped };
}

export function main() {
  const totals = Object.fromEntries(KINDS.map((k) => [k, { valid: 0, invalid: 0 }]));
  let skipped = 0;

  const check = (kind, rec) => {
    const result = validate(kind, rec);
    totals[kind][result.ok ? "valid" : "invalid"]++;
  };
  const readJson = (rel) => {
    const file = path.join(ROOT, rel);
    return fs.existsSync(file) ? JSON.parse(fs.readFileSync(file, "utf8")) : null;
  };
  const list = (rel, ext) => {
    const dir = path.join(ROOT, rel);
    return fs.existsSync(dir) ? fs.readdirSync(dir).filter((f) => f.endsWith(ext)).map((f) => path.join(dir, f)) : [];
  };

  const incident = readJson("labs/review/sample-incident.json");
  if (incident) check("incident", incident);

  for (const file of list("os/worlds/science-lab/records/cycles", ".json")) check("cycle", JSON.parse(fs.readFileSync(file, "utf8")));

  const findings = readJsonl(path.join(ROOT, "os-build/aegis/findings.jsonl"));
  skipped += findings.skipped;
  for (const rec of findings.records) check("aegis-finding", rec);

  for (const file of list("os-build/logs/wave3-model-proofs", ".jsonl")) {
    const receipts = readJsonl(file);
    skipped += receipts.skipped;
    for (const rec of receipts.records) check("model-receipt", rec);
  }

  const registry = readJson("agents/registry.json");
  for (const entry of registry?.agents || []) {
    check("registry-entry", entry);
    for (const target of entry.watch || []) check("watch-target", target);
  }

  const bootFile = path.join(ROOT, "os-build/BOOT_LOG_INDEX.md");
  if (fs.existsSync(bootFile)) {
    for (const row of parseBootIndex(fs.readFileSync(bootFile, "utf8"))) check("boot-log-index-row", row);
  }

  const proofFile = path.join(ROOT, "os-build/PROGRAM_PROOF_LEDGER.md");
  if (fs.existsSync(proofFile)) {
    for (const row of parseProofLedger(fs.readFileSync(proofFile, "utf8"))) check("proof-ledger-row", row);
  }

  const runsDir = path.join(ROOT, "runs");
  if (fs.existsSync(runsDir)) {
    for (const dir of fs.readdirSync(runsDir)) {
      const file = path.join(runsDir, dir, "baton.json");
      if (fs.existsSync(file)) check("baton-handoff", JSON.parse(fs.readFileSync(file, "utf8")));
    }
  }

  console.log("validate_all: " + KINDS.length + " schemas");
  for (const kind of KINDS) {
    console.log("  " + kind + ": " + totals[kind].valid + " valid, " + totals[kind].invalid + " invalid");
  }
  if (skipped) console.log("  skipped torn jsonl lines: " + skipped);
  const valid = KINDS.reduce((n, k) => n + totals[k].valid, 0);
  const invalid = KINDS.reduce((n, k) => n + totals[k].invalid, 0);
  console.log("total: " + valid + " valid, " + invalid + " invalid");
  if (invalid) process.exitCode = 1;
}

if (process.argv[1] && path.resolve(process.argv[1]) === url.fileURLToPath(import.meta.url)) main();
