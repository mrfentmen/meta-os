// CB-051..060 — schema and validator tests. One good and at least three bad
// records for the incident shape; good/bad for the rest; the CLI must report
// counts without echoing a record.
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import url from "node:url";
import { spawnSync } from "node:child_process";
import { SCHEMAS, KINDS, validate, parseBootIndex, parseProofLedger } from "../tools/validate_all.mjs";

const ROOT = path.resolve(path.dirname(url.fileURLToPath(import.meta.url)), "..");
const HEX = "a".repeat(64);

const goodIncident = () => ({
  incident: {
    id: "SIM-2026-11-01-001", simulated: true, product: "medicus", category: "person on ground",
    tier: "yellow", timestamp: "2026-11-01T10:00:00Z", camera: "Canal Street",
    description: "Adult lying flat on the sidewalk.", identity: "UNIDENTIFIED", visible_marks: ["dark jacket"],
  },
  evidence: { frames: ["SIM-frame-001.jpg"], face_boxes: [] },
});
const goodCycle = () => ({ cycle_id: "CYCLE-1", phase: "wetlab", gate_state: "open", history: [HEX], inputs: {}, outputs: {} });
const goodFinding = () => ({
  ts: "2026-11-02T11:11:27.338Z", v: 1, severity: "medium", title: "no DMARC record",
  evidence: "DNS query returned no v=DMARC1 record.", source: "aegis/osint.mjs", run: "osint-1",
});
const goodReceipt = () => ({
  ts: "2026-11-02T14:26:20.657873+00:00", kind: "chat", model: "muse-wonder-1.0", surface: "chat",
  usage: { total_tokens: 89 }, latency_ms: 1164, est_cost_usd: null,
});
const goodRegistry = () => ({ name: "rowan", lane: "kernel", command: ["true"], budget: { maxWallMs: 1000 } });
const goodBootRow = () => ({ file: "K1-boot.txt", lines: 54, first_marker: "META OS KERNEL - alive (K1)" });
const goodProofRow = () => ({ program: "Queue", command: "pytest", count: 277, evidence: "logs/q.log" });
const goodWatch = () => ({ type: "file", path: "/repo/.git/HEAD" });
const goodBaton = () => ({ jobId: "run-1", authors: ["bond", "pax"] });

test("CB-051..059: the schema bundle defines every kind", () => {
  assert.equal(KINDS.length, 9);
  for (const kind of KINDS) assert.equal(SCHEMAS.$defs[kind].type, "object", kind);
});

test("CB-051 incident: one good and three bad records", () => {
  assert.equal(validate("incident", goodIncident()).ok, true);
  const noId = goodIncident(); delete noId.incident.id;
  const badTier = goodIncident(); badTier.incident.tier = "blue";
  const noFrames = goodIncident(); delete noFrames.evidence.frames;
  for (const [name, rec] of [["no id", noId], ["bad tier", badTier], ["no frames", noFrames]]) {
    const result = validate("incident", rec);
    assert.equal(result.ok, false, name);
    assert.ok(result.errors.length > 0, name);
  }
});

test("CB-052 cycle: phase outside the lab stages is refused", () => {
  assert.equal(validate("cycle", goodCycle()).ok, true);
  const bad = goodCycle(); bad.phase = "shipping";
  assert.equal(validate("cycle", bad).ok, false);
});

test("CB-053 aegis: severity is checked and a secret-shaped value is refused", () => {
  assert.equal(validate("aegis-finding", goodFinding()).ok, true);
  const badSeverity = goodFinding(); badSeverity.severity = "urgent";
  assert.equal(validate("aegis-finding", badSeverity).ok, false);
  const secret = goodFinding(); secret.evidence = "token sk-" + "a".repeat(32);
  const result = validate("aegis-finding", secret);
  assert.equal(result.ok, false);
  assert.match(result.errors.join(" "), /secret-shaped value in evidence/);
});

test("CB-054 model receipt: missing model and negative latency are refused", () => {
  assert.equal(validate("model-receipt", goodReceipt()).ok, true);
  const noModel = goodReceipt(); delete noModel.model;
  const negative = goodReceipt(); negative.latency_ms = -1;
  assert.equal(validate("model-receipt", noModel).ok, false);
  assert.equal(validate("model-receipt", negative).ok, false);
});

test("CB-055 registry entry: wired to the runtime validator", () => {
  assert.equal(validate("registry-entry", goodRegistry()).ok, true);
  const noLane = goodRegistry(); delete noLane.lane;
  const noCommand = goodRegistry(); noCommand.command = [];
  assert.equal(validate("registry-entry", noLane).ok, false);
  assert.equal(validate("registry-entry", noCommand).ok, false);
});

test("CB-056 boot-log index: generator rows validate, bad line count refused", () => {
  assert.equal(validate("boot-log-index-row", goodBootRow()).ok, true);
  const bad = goodBootRow(); bad.lines = -1;
  assert.equal(validate("boot-log-index-row", bad).ok, false);
  const rows = parseBootIndex(fs.readFileSync(path.join(ROOT, "os-build/BOOT_LOG_INDEX.md"), "utf8"));
  assert.ok(rows.length > 0);
  for (const row of rows) assert.equal(validate("boot-log-index-row", row).ok, true, row.file);
});

test("CB-057 proof ledger: command, count and evidence are required", () => {
  assert.equal(validate("proof-ledger-row", goodProofRow()).ok, true);
  const bad = goodProofRow(); delete bad.evidence;
  assert.equal(validate("proof-ledger-row", bad).ok, false);
  const rows = parseProofLedger(fs.readFileSync(path.join(ROOT, "os-build/PROGRAM_PROOF_LEDGER.md"), "utf8"));
  assert.ok(rows.length > 0);
  for (const row of rows) assert.equal(validate("proof-ledger-row", row).ok, true, row.program);
});

test("CB-058 watch target: only the poller's file shape is accepted", () => {
  assert.equal(validate("watch-target", goodWatch()).ok, true);
  const bad = goodWatch(); bad.type = "url";
  assert.equal(validate("watch-target", bad).ok, false);
});

test("CB-059 baton handoff: a chain needs a job id and named authors", () => {
  assert.equal(validate("baton-handoff", goodBaton()).ok, true);
  const bad = goodBaton(); bad.authors = [];
  assert.equal(validate("baton-handoff", bad).ok, false);
});

test("CB-060 validate_all reports counts only", () => {
  const run = spawnSync(process.execPath, ["tools/validate_all.mjs"], { cwd: ROOT, encoding: "utf8" });
  assert.equal(run.status, 0, run.stderr || run.stdout);
  assert.match(run.stdout, /total: \d+ valid, 0 invalid/);
  assert.doesNotMatch(run.stdout, /no DMARC record/);
});
