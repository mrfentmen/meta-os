// R13-376..400 — 25 Hands-Free intake cases through the real text-first path.
//
// Each case runs `parseInbox`/`dropOrders` on a real temp inbox (the same functions the hosted
// intake calls), records what was filed and what was refused, and — where the case names a loop
// — asks the real `spawnHosted` gate whether that loop would start.
//
// The assertions are deliberately about invariants, not about wishes:
//   * nothing is silently dropped: every non-empty, non-comment line is filed or refused with a
//     reason (R11-288's rule, held at the intake);
//   * a refusal is a refusal, not a crash;
//   * a case that names a fence (draft loop, dispatch) records the fence's answer.
// What the path actually does with each input is written to P_CASES.json by the after() hook.
// A finding here is the measured behaviour, including the fences that turned out not to exist.
//
//   node --test handsfree/intake_cases.test.mjs
import { test, after } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import url from "node:url";
import { parseInbox, dropOrders } from "./intake.mjs";
import { classifyUtterance } from "./refusals.mjs";
import { spawnHosted } from "../agents/hosted.mjs";
import { resolveCommand, loadRegistry } from "../agents/runtime.mjs";

const HERE = path.dirname(url.fileURLToPath(import.meta.url));
const ROOT = path.dirname(HERE);
const WORK = path.join(ROOT, "os-build", "round13", "handsfree");
const TMP = path.join(WORK, "tmp");
const rows = [];

function runIntake(task, label, text, extra = {}) {
  const dir = path.join(TMP, task);
  fs.rmSync(dir, { recursive: true, force: true });
  fs.mkdirSync(dir, { recursive: true });
  const inbox = path.join(dir, "inbox.txt");
  fs.writeFileSync(inbox, text);
  const jobsDir = path.join(dir, "jobs");
  const r = dropOrders(inbox, jobsDir, { now: 1767225600000, source: "round13-drill" });

  const lines = text.split(/\r?\n/).map((l) => l.trim()).filter((l) => l && !l.startsWith("#"));
  const refusals = lines.map((l) => ({ line: l, ...classifyUtterance(l) })).filter((x) => x.refused);

  // dropOrders returns {id, agent} only; the order text lives in the job file it wrote. Reading it
  // back is the honest record — it is also the file the watchman would pick up.
  const filed = r.jobs.map((j) => {
    let rec = null;
    try { rec = JSON.parse(fs.readFileSync(path.join(jobsDir, j.id + ".job.json"), "utf8")); } catch { /* torn */ }
    return { id: j.id, agent: j.agent, orders: rec ? rec.orders : null, source: rec ? rec.source : null };
  });

  const row = {
    task, case: label,
    input_lines: lines.length,
    filed,
    skipped: r.skipped,
    refusals,
    inbox_after: fs.readFileSync(inbox, "utf8"),
    ...extra,
  };
  rows.push(row);
  return row;
}

// Invariant for every intake case: filed + skipped accounts for every line. No silent drop.
function assertAccounted(row) {
  assert.equal(row.filed.length + row.skipped.length, row.input_lines,
    row.task + ": " + (row.input_lines - row.filed.length - row.skipped.length) + " line(s) silently dropped");
}

test("R13-376 plain text order intake", () => {
  const r = runIntake("R13-376", "plain text order intake", "aegis: run the local passes\n");
  assertAccounted(r);
  assert.equal(r.filed.length, 1);
  assert.equal(r.filed[0].agent, "aegis");
  assert.equal(r.filed[0].orders, "run the local passes");
});

test("R13-377 multi-line intake", () => {
  const r = runIntake("R13-377", "multi-line intake",
    "aegis: run the local passes\nnervus: file one stub record\nhandsfree-intake: take the inbox\n");
  assertAccounted(r);
  assert.equal(r.filed.length, 3);
});

test("R13-378 empty intake", () => {
  const r = runIntake("R13-378", "empty intake", "");
  assertAccounted(r);
  assert.equal(r.filed.length, 0);
  assert.equal(r.skipped.length, 0);
});

test("R13-379 whitespace-only intake", () => {
  const r = runIntake("R13-379", "whitespace-only intake", "   \n\t\n \r\n");
  assertAccounted(r);
  assert.equal(r.filed.length, 0);
});

test("R13-380 oversized intake (over the cap)", () => {
  const big = "aegis: " + "x".repeat(200000) + "\n";
  const r = runIntake("R13-380", "oversized intake (over the cap)", big, {
    finding: "no size cap exists: the whole 200 KB order is filed as one job",
  });
  assertAccounted(r);
  assert.equal(r.filed.length, 1, "the intake has no cap, so the oversized line is filed");
  assert.ok(r.filed[0].orders.length > 100000);
});

test("R13-381 intake with control characters", () => {
  const r = runIntake("R13-381", "intake with control characters",
    "aegis: run\u0000the\u0007passes\n", { finding: null });
  assertAccounted(r);
  r.observation = r.filed.length
    ? "control characters are preserved into the job file unmodified"
    : "refused";
});

test("R13-382 intake with unicode text", () => {
  const r = runIntake("R13-382", "intake with unicode text",
    "nervus: vérifier les contrats — 检测\n");
  assertAccounted(r);
  assert.equal(r.filed.length, 1);
});

test("R13-383 intake with a URL", () => {
  const r = runIntake("R13-383", "intake with a URL",
    "aegis: fetch https://example.com/report and file it\n",
    { finding: "the intake does not inspect URLs; the order is filed verbatim" });
  assertAccounted(r);
  assert.equal(r.filed.length, 1);
});

test("R13-384 intake with a file path", () => {
  const r = runIntake("R13-384", "intake with a file path",
    "nervus: write the result to /etc/hosts\n",
    { finding: "the intake does not inspect paths; an absolute path is prose in the order" });
  assertAccounted(r);
  assert.equal(r.filed.length, 1);
});

test("R13-385 intake naming a loop that is draft", () => {
  const registry = loadRegistry(path.join(ROOT, "agents", "registry.json"));
  const draft = registry.find((a) => a.name === "musica-studio");
  assert.ok(draft && draft.draft === true, "musica-studio is a draft entry");
  const gate = spawnHosted({ ...draft, command: resolveCommand(draft.command, ROOT) }, { root: TMP });
  const r = runIntake("R13-385", "intake naming a loop that is draft",
    "musica-studio: play the new session\n", { fence: gate });
  assertAccounted(r);
  assert.equal(r.filed.length, 1, "intake files the order");
  assert.equal(gate.ok, false, "the spawn gate refuses a draft loop");
  assert.equal(gate.reason, "draft-agent");
});

test("R13-386 intake naming a loop that is real", async () => {
  const registry = loadRegistry(path.join(ROOT, "agents", "registry.json"));
  const real = registry.find((a) => a.name === "aegis");
  assert.ok(real && real.hosted === true && real.draft !== true, "aegis is a hosted, non-draft entry");
  // The gate's answer is proved with a command that exits at once. Section O already ran the real
  // loop eight times; re-running it here would measure the loop, not the gate, and would leave a
  // live child holding the test process open.
  const gate = spawnHosted({ name: "gate-probe", hosted: true,
    command: [process.execPath, "-e", "process.exit(0)"], budget: {} }, { root: TMP });
  const fence = { ok: gate.ok, reason: gate.reason || null };
  if (gate.ok) await gate.handle.done;   // it exits on its own; killing at once leaves the pipe open
  const r = runIntake("R13-386", "intake naming a loop that is real",
    "aegis: run the local passes\n", { fence });
  assertAccounted(r);
  assert.equal(gate.ok, true, "a hosted, non-draft entry passes the gate");
});

test("R13-387 intake with an urgent flag", () => {
  const r = runIntake("R13-387", "intake with an urgent flag",
    "aegis: URGENT run the passes now\n",
    { finding: "the job record has no priority field: 'URGENT' stays prose inside orders" });
  assertAccounted(r);
  assert.equal(r.filed.length, 1);
});

test("R13-388 intake with a budget note", () => {
  const r = runIntake("R13-388", "intake with a budget note",
    "aegis: run with a 5 minute budget\n",
    { finding: "a budget named in text is prose; the job record carries no budget field" });
  assertAccounted(r);
  assert.equal(r.filed.length, 1);
});

test("R13-389 intake with a STOP request", () => {
  const r = runIntake("R13-389", "intake with a STOP request",
    "aegis: STOP\n",
    { finding: "a spoken STOP is filed as a job; the intake never writes a STOP file" });
  assertAccounted(r);
  assert.equal(r.filed.length, 1);
  assert.equal(r.filed[0].orders, "STOP");
});

test("R13-390 intake with a status question", () => {
  const r = runIntake("R13-390", "intake with a status question", "what is running right now?\n");
  assertAccounted(r);
  assert.equal(r.filed.length, 0, "a line with no agent prefix is not guessed at");
  assert.equal(r.skipped.length, 1);
  assert.match(r.skipped[0].reason, /agent before a colon/);
});

test("R13-391 intake with two jobs", () => {
  const r = runIntake("R13-391", "intake with two jobs",
    "aegis: first\naegis: second\n");
  assertAccounted(r);
  assert.equal(r.filed.length, 2);
  assert.notEqual(r.filed[0].id, r.filed[1].id);
});

test("R13-392 intake repeating a finished job", () => {
  const r = runIntake("R13-392", "intake repeating a finished job",
    "aegis: run the local passes\naegis: run the local passes\n",
    { finding: "the same order filed twice becomes two jobs with different ids; no duplicate check exists at the intake" });
  assertAccounted(r);
  assert.equal(r.filed.length, 2);
  assert.notEqual(r.filed[0].id, r.filed[1].id);
});

test("R13-393 intake contradicting a standing fence", () => {
  const r = runIntake("R13-393", "intake contradicting a standing fence",
    "aegis: edit kernel/src/main.rs and rewrite syscalls.rs\n",
    { finding: "the intake does not know the kernel fence; the order is filed with an agent that cannot legally do it" });
  assertAccounted(r);
  assert.equal(r.filed.length, 1);
});

test("R13-394 intake with a dispatch request (must stay simulated)", () => {
  const dispatch = "pax: send the finished report to the boss";
  const refusal = classifyUtterance(dispatch);
  const r = runIntake("R13-394", "intake with a dispatch request", dispatch + "\n", {
    fence: { refusal, wired_into_intake: false },
    finding: "the refusal catalogue catches 'send', but intake.mjs never calls it: the order is still filed",
  });
  assertAccounted(r);
  assert.equal(refusal.refused, true, "the catalogue refuses the dispatch");
  assert.equal(refusal.id, "send");
  assert.equal(r.filed.length, 1, "and the intake files it anyway — the catalogue is not wired in");
});

test("R13-395 intake in all caps", () => {
  const r = runIntake("R13-395", "intake in all caps",
    "AEGIS: RUN THE PASSES\n",
    { finding: "agent names are not case-normalised: 'AEGIS' will not match the 'aegis' registry entry" });
  assertAccounted(r);
  assert.equal(r.filed[0].agent, "AEGIS");
});

test("R13-396 intake with punctuation only", () => {
  const r = runIntake("R13-396", "intake with punctuation only", "...\n---\n!!!\n");
  assertAccounted(r);
  assert.equal(r.filed.length, 0);
  assert.equal(r.skipped.length, 3);
});

test("R13-397 intake with a pasted log", () => {
  const r = runIntake("R13-397", "intake with a pasted log",
    "12:00 INFO boot start\n12:01 INFO devices ok\n", {
      finding: "every colon-bearing line becomes an order: '12' and '12' are read as agent names",
    });
  assertAccounted(r);
  assert.equal(r.filed.length, 2);
  assert.equal(r.filed[0].agent, "12");
});

test("R13-398 intake with a pasted error", () => {
  const r = runIntake("R13-398", "intake with a pasted error",
    "Error: ENOENT no such file or directory\n", {
      finding: "a pasted stack or error line is filed as an order for an agent named 'Error'",
    });
  assertAccounted(r);
  assert.equal(r.filed.length, 1);
  assert.equal(r.filed[0].agent, "Error");
});

test("R13-399 intake with a date and time", () => {
  const r = runIntake("R13-399", "intake with a date and time",
    "2026-11-02 14:30: aegis run the passes\n", {
      finding: "the timestamp before the colon becomes the agent name; the real agent is buried in orders",
    });
  assertAccounted(r);
  assert.equal(r.filed[0].agent, "2026-11-02 14");
});

test("R13-400 intake with no verb", () => {
  const r = runIntake("R13-400", "intake with no verb",
    "aegis: the thing\n", {
      finding: "there is no verb check: an order with no action is filed like any other",
    });
  assertAccounted(r);
  assert.equal(r.filed.length, 1);
});

after(() => {
  fs.mkdirSync(WORK, { recursive: true });
  const findings = rows.filter((r) => r.finding).map((r) => ({ task: r.task, finding: r.finding }));
  const counts = {
    total: rows.length,
    filed_ok: rows.filter((r) => r.filed.length > 0).length,
    refused: rows.filter((r) => r.skipped.length > 0).length,
    fences_checked: rows.filter((r) => r.fence).length,
    findings: findings.length,
  };
  fs.writeFileSync(path.join(WORK, "P_CASES.json"),
    JSON.stringify({ tool: "handsfree/intake_cases.test.mjs", ran_at: new Date().toISOString(), counts, rows, findings }, null, 2) + "\n");

  const table = ["| task | case | filed | refused | finding |", "|---|---|---|---|---|"];
  for (const r of rows) {
    table.push("| " + r.task + " | " + r.case + " | " + r.filed.length + " | " + r.skipped.length + " | "
      + String(r.finding || "").replace(/\|/g, "\\|").slice(0, 150) + " |");
  }
  fs.writeFileSync(path.join(WORK, "SECTION_P.md"),
    "# Section P — Hands-Free intake cases (R13-376..400)\n\n"
    + "Run: `node --test handsfree/intake_cases.test.mjs`. Machine record: `P_CASES.json`.\n\n"
    + "Counts: " + JSON.stringify(counts) + "\n\n"
    + "Every case runs the real `parseInbox`/`dropOrders`; the two loop cases ask the real "
    + "`spawnHosted` gate. A finding is the measured behaviour — several of them are fences that "
    + "were expected to exist and do not.\n\n"
    + table.join("\n") + "\n");
  fs.rmSync(TMP, { recursive: true, force: true });
  console.log("P_CASES " + JSON.stringify(counts));
});
