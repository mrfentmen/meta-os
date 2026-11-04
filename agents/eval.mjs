// Meta OS agent layer — offline eval harness (R2-T3 patrol lane, tasks 68-75).
//
// Twelve stub-provider tasks (agents/eval_tasks.json), each with a pass/fail
// definition. Every task writes an ARTIFACT file and is scored by reading
// that artifact back — never by judging prose. The whole run is offline:
// an in-memory board on loopback, in-process stubs, and local python3 stdlib.
//
//   node agents/eval.mjs [--results-dir DIR] [--tasks FILE] [--only ID] [--gate] [--last10] [--json]
//
// Results land in <results-dir>/eval-<ts>.json: {ts, iso, commit, provider,
// score, passed, failed, total, tasks:[{id,name,area,pass,ok,artifact,detail}]}.
// Exit codes: 0 all pass; 1 any task failed; 2 regression gate tripped
// (--gate fails when the score drops below the last recorded score).
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import url from "node:url";
import { execSync, spawnSync } from "node:child_process";
import { createBoardServer, notifyId } from "../board/board.mjs";
import { retryJob } from "./jobs.mjs";
import { notify } from "./notify.mjs";
import { createWatchman } from "./watchman.mjs";
import { beatDaily, heartbeatFile } from "./heartbeat.mjs";
import { cleanupStaleRuns } from "./cleanup.mjs";

const HERE = path.dirname(url.fileURLToPath(import.meta.url));
const REPO = path.dirname(HERE);
export const PROVIDER = "stub (offline: in-process stubs, loopback board, local python3 stdlib only; no network, no paid calls)";

export function defaultResultsDir() {
  return path.join(HERE, "eval-results");
}

export function gitCommit(repoRoot = REPO) {
  try {
    return execSync("git rev-parse HEAD", { cwd: repoRoot, encoding: "utf8" }).trim();
  } catch {
    return "unknown";
  }
}

export function loadTasks(file) {
  const raw = JSON.parse(fs.readFileSync(file, "utf8"));
  if (!Array.isArray(raw.tasks) || raw.tasks.length === 0) throw new Error("eval: tasks file has no tasks");
  return raw.tasks;
}

function writeArtifact(dir, name, data) {
  const p = path.join(dir, name);
  fs.writeFileSync(p, typeof data === "string" ? data : JSON.stringify(data, null, 2) + "\n");
  return p;
}

function readArtifact(p) {
  return fs.readFileSync(p, "utf8");
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function withBoard(fn) {
  const server = createBoardServer();
  await new Promise((res) => server.listen(0, "127.0.0.1", res));
  const port = server.address().port;
  try {
    return await fn(`http://127.0.0.1:${port}`);
  } finally {
    await new Promise((res) => server.close(res));
  }
}

async function postJson(base, p, body) {
  const r = await fetch(base + p, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  let json = null;
  try {
    json = await r.json();
  } catch { /* error bodies are still JSON per board.mjs, but never assume */ }
  return { status: r.status, json };
}

/* ---- one check per task id; each writes its artifact, then scores it ---- */

const CHECKS = {
  "bus-post-read": async (task, ctx) => {
    const got = await withBoard(async (base) => {
      const posted = await postJson(base, "/rooms/eval-bus/messages", { nick: "eval", text: "hello bus" });
      const r = await fetch(base + "/rooms/eval-bus/messages?since=-1");
      return { posted, read: { status: r.status, json: await r.json() } };
    });
    writeArtifact(ctx.artifacts, task.artifact, got);
    const back = JSON.parse(readArtifact(path.join(ctx.artifacts, task.artifact)));
    const line = back.read.json && back.read.json.messages && back.read.json.messages[0];
    const ok = back.posted.status === 201 && back.posted.json && back.posted.json.index === 0
      && typeof line === "string" && line.startsWith("eval: hello bus");
    return { ok, detail: ok ? "index 0, line round-trips" : "roundtrip mismatch: " + JSON.stringify(back).slice(0, 300) };
  },

  "bus-room-validation": async (task, ctx) => {
    const got = await withBoard(async (base) => ({
      badRoom: await postJson(base, "/rooms/BAD/messages", { nick: "eval", text: "x" }),
      badSev: await postJson(base, "/rooms/eval-bus/notify", { severity: "bogus", topic: "t", text: "x" }),
    }));
    writeArtifact(ctx.artifacts, task.artifact, got);
    const back = JSON.parse(readArtifact(path.join(ctx.artifacts, task.artifact)));
    const ok = back.badRoom.status === 400 && back.badRoom.json && typeof back.badRoom.json.error === "string"
      && back.badSev.status === 400 && back.badSev.json && typeof back.badSev.json.error === "string";
    return { ok, detail: ok ? "both refused 400 with JSON errors" : "expected two 400s" };
  },

  "bus-notify-id": async (task, ctx) => {
    const a = notifyId("eval-bus", "unit-failed", "critical", "oc2-trio stopped");
    const b = notifyId("eval-bus", "unit-failed", "critical", "oc2-trio stopped");
    writeArtifact(ctx.artifacts, task.artifact, { id: a, repeat: b });
    const back = JSON.parse(readArtifact(path.join(ctx.artifacts, task.artifact)));
    const ok = back.id === back.repeat && /^ntf-[0-9a-f]{16}$/.test(back.id);
    return { ok, detail: ok ? back.id + " deterministic" : "id mismatch: " + back.id + " vs " + back.repeat };
  },

  "queue-retry": async (task, ctx) => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), "eval-retry-"));
    const jobsDir = path.join(root, "jobs");
    fs.mkdirSync(jobsDir, { recursive: true });
    const job = { id: "q-1", agent: "demo", orders: "probe" };
    fs.writeFileSync(path.join(jobsDir, "q-1.job.json"), JSON.stringify(job));
    fs.writeFileSync(path.join(jobsDir, "q-1.result.json"),
      JSON.stringify({ id: "q-1", agent: "demo", run: "run-abc", code: 1, finishedAt: new Date().toISOString() }));
    const first = retryJob({ root, id: "q-1" });
    const second = retryJob({ root, id: "q-1" });
    const files = fs.readdirSync(jobsDir).filter((f) => f.startsWith("q-1-r")).sort();
    writeArtifact(ctx.artifacts, task.artifact, { first, second, files });
    const back = JSON.parse(readArtifact(path.join(ctx.artifacts, task.artifact)));
    const ok = back.first.ok === true && back.first.id === "q-1-r2" && back.first.continuesFrom === "run-abc"
      && back.second.ok === true && back.second.existing === true && back.files.length === 1;
    return { ok, detail: ok ? "r2 continues run-abc, repeat idempotent" : JSON.stringify(back).slice(0, 300) };
  },

  "queue-retry-refuses-clean": async (task, ctx) => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), "eval-retry-clean-"));
    const jobsDir = path.join(root, "jobs");
    fs.mkdirSync(jobsDir, { recursive: true });
    fs.writeFileSync(path.join(jobsDir, "q-9.job.json"), JSON.stringify({ id: "q-9", agent: "demo", orders: "x" }));
    fs.writeFileSync(path.join(jobsDir, "q-9.result.json"),
      JSON.stringify({ id: "q-9", agent: "demo", run: "run-zzz", code: 0, finishedAt: new Date().toISOString() }));
    const out = retryJob({ root, id: "q-9" });
    writeArtifact(ctx.artifacts, task.artifact, out);
    const back = JSON.parse(readArtifact(path.join(ctx.artifacts, task.artifact)));
    const ok = back.ok === false && /cleanly|finished cleanly/.test(back.reason || "");
    return { ok, detail: ok ? "refused: " + back.reason : "clean job was retryable!" };
  },

  "receipt-valid": async (task, ctx) => {
    const lines = [
      { ts: "2026-11-04T00:00:00Z", kind: "assess", model: "muse-spark", surface: "trio", usage: {}, latency_ms: 120, est_cost_usd: 0.002 },
      { ts: "2026-11-04T00:00:01Z", kind: "assess", model: "meta-spark-7", endpoint: "trio", usage: {}, latency_ms: 0, estimate: 0 },
    ].map((o) => JSON.stringify(o)).join("\n") + "\n";
    const file = writeArtifact(ctx.artifacts, task.artifact, lines);
    const r = spawnSync("python3", [path.join(REPO, "server/queue/receipt_validate.py"), file], { encoding: "utf8" });
    const ok = r.status === 0;
    return { ok, detail: ok ? String(r.stdout).trim().split("\n").pop() : "exit " + r.status + ": " + String(r.stdout || r.stderr).slice(0, 200) };
  },

  "receipt-tamper": async (task, ctx) => {
    const lines = [
      { ts: "2026-11-04T00:00:00Z", kind: "assess", model: "muse-spark", surface: "trio", usage: {}, latency_ms: 40, est_cost_usd: 0.001 },
      { ts: "2026-11-04T00:00:01Z", kind: "assess", model: "local-cpu", surface: "trio", usage: {}, latency_ms: 50, est_cost_usd: 0.01 },
      { ts: "2026-11-04T00:00:02Z", kind: "assess", model: "muse-spark", surface: "trio", usage: {}, latency_ms: -5, est_cost_usd: 0.001 },
    ].map((o) => JSON.stringify(o)).join("\n") + "\n";
    const file = writeArtifact(ctx.artifacts, task.artifact, lines);
    const r = spawnSync("python3", [path.join(REPO, "server/queue/receipt_validate.py"), file], { encoding: "utf8" });
    const out = String(r.stdout || "") + String(r.stderr || "");
    const report = { exit: r.status, output: out };
    writeArtifact(ctx.artifacts, "receipt_tamper_report.json", report);
    const back = JSON.parse(readArtifact(path.join(ctx.artifacts, "receipt_tamper_report.json")));
    const ok = back.exit === 1 && /line 2/.test(back.output) && /line 3/.test(back.output);
    return { ok, detail: ok ? "exit 1, lines 2+3 named" : "exit " + back.exit + ": " + back.output.slice(0, 200) };
  },

  "patrol-empty-record": async (task, ctx) => {
    // Runs the REAL patrol.py Patrol class with an empty camera list. Heavy
    // crew modules are stubbed in sys.modules (offline, no side effects); the
    // budget guard, priority math and status write are the shipped code.
    const probeDir = fs.mkdtempSync(path.join(os.tmpdir(), "eval-patrol-"));
    const snippet = `
import sys, types, json
for _name in ["crew", "crew_common", "crew_records", "spark_guardrail"]:
    sys.modules[_name] = types.ModuleType(_name)
import crew_common, spark_guardrail
crew_common.now_iso = lambda: "2026-11-04T00:00:00Z"
crew_common.distance_meters = lambda a, b: 10 ** 9
class GuardrailStop(Exception): pass
spark_guardrail.GuardrailStop = GuardrailStop
spark_guardrail.check = lambda: None
spark_guardrail.status = lambda: {"remaining_usd": 100.0}
sys.path.insert(0, ${JSON.stringify(path.join(REPO, "server", "queue"))})
import patrol
class FakeRecords(object):
    def __init__(self, d):
        self.dir = d; self.statuses = []; self.events = []
    def write_status(self, s):
        self.statuses.append(s); return s
    def append_event(self, e):
        self.events.append(e)
    def open_incidents(self): return []
    def recent_events(self, n): return []
rec = FakeRecords(${JSON.stringify(probeDir)})
p = patrol.Patrol(crew_obj=object(), cameras=[], camera_source="test-empty",
                  records=rec, interval_s=0,
                  guardrail_status=lambda: {"remaining_usd": 100.0},
                  sleep=lambda s: None)
outcome = p.run_cycle()
print(json.dumps({"outcome": outcome.get("outcome"), "status": rec.statuses[-1] if rec.statuses else None}))
`;
    const snipFile = path.join(probeDir, "probe.py");
    fs.writeFileSync(snipFile, snippet);
    const r = spawnSync("python3", [snipFile], { encoding: "utf8", timeout: 60000 });
    if (r.status !== 0) return { ok: false, detail: "probe exit " + r.status + ": " + String(r.stderr).slice(0, 300) };
    let parsed;
    try {
      parsed = JSON.parse(String(r.stdout).trim().split("\n").pop());
    } catch {
      return { ok: false, detail: "probe printed no JSON: " + String(r.stdout).slice(0, 200) };
    }
    writeArtifact(ctx.artifacts, task.artifact, parsed);
    const back = JSON.parse(readArtifact(path.join(ctx.artifacts, task.artifact)));
    const ok = back.outcome === "no-cameras" && back.status && back.status.state === "idle";
    return { ok, detail: ok ? "outcome no-cameras, status idle recorded" : JSON.stringify(back).slice(0, 300) };
  },

  "watchman-alert": async (task, ctx) => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), "eval-watch-"));
    const jobsDir = path.join(root, "jobs");
    fs.mkdirSync(jobsDir, { recursive: true });
    const registryFile = path.join(root, "registry.json");
    fs.writeFileSync(registryFile, JSON.stringify({ agents: [{
      name: "fail-fast", lane: "eval", command: [process.execPath, "-e", "process.exit(1)"], budget: {},
    }] }));
    fs.writeFileSync(path.join(jobsDir, "eval-fail-1.job.json"),
      JSON.stringify({ id: "eval-fail-1", agent: "fail-fast", orders: "eval probe" }));
    const w = createWatchman({ registryFile, root, jobsDir, repoRoot: root });
    const spawned = await w.pollOnce();
    await Promise.allSettled(spawned.map((s) => s.handle.done));
    await sleep(50);
    let notices = [];
    for (let i = 0; i < 60 && notices.length === 0; i++) {
      try {
        notices = fs.readFileSync(path.join(root, "notices.jsonl"), "utf8")
          .split("\n").filter(Boolean).map((l) => JSON.parse(l));
        notices = notices.filter((n) => n.key === "job:eval-fail-1:failed");
      } catch { notices = []; }
      if (notices.length === 0) await sleep(50);
    }
    writeArtifact(ctx.artifacts, task.artifact, notices);
    const back = JSON.parse(readArtifact(path.join(ctx.artifacts, task.artifact)));
    const alarm = back.find((n) => n.severity === "alarm" && n.suppressed !== true) || back[0];
    const ok = Boolean(alarm) && alarm.severity === "alarm"
      && (alarm.title || "").includes("fail-fast") && /exit 1/.test(alarm.body || "");
    return { ok, detail: ok ? "alarm names fail-fast + exit 1" : "no naming alarm: " + JSON.stringify(back).slice(0, 300) };
  },

  "dedupe-window": async (task, ctx) => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), "eval-dedupe-"));
    const records = [];
    for (let i = 0; i < 10; i++) {
      records.push(await notify({
        root, severity: "alarm", key: "unit:oc2-trio:failed",
        title: "Unit failed: oc2-trio", body: "unit oc2-trio failed: exit 1",
      }));
    }
    const journal = fs.readFileSync(path.join(root, "notices.jsonl"), "utf8").split("\n").filter(Boolean);
    const summary = { sent: 10, journalLines: journal.length, rung: records.filter((r) => !r.suppressed).length };
    writeArtifact(ctx.artifacts, task.artifact, summary);
    const back = JSON.parse(readArtifact(path.join(ctx.artifacts, task.artifact)));
    const ok = back.sent === 10 && back.journalLines === 10 && back.rung === 1;
    return { ok, detail: ok ? "10 sends, 1 bell, 9 suppressed" : JSON.stringify(back) };
  },

  "heartbeat-daily": async (task, ctx) => {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), "eval-beat-"));
    const day1 = Date.UTC(2026, 10, 3, 12, 0, 0);
    const a = beatDaily({ dir, now: day1, scheduler: "oc2-eval.timer", commit: "abc123" });
    const b = beatDaily({ dir, now: day1 + 3600 * 1000, scheduler: "oc2-eval.timer", commit: "abc123" });
    const c = beatDaily({ dir, now: day1 + 86400 * 1000, scheduler: "oc2-eval.timer", commit: "def456" });
    const lines = fs.readFileSync(heartbeatFile(dir), "utf8").split("\n").filter(Boolean).map((l) => JSON.parse(l));
    writeArtifact(ctx.artifacts, task.artifact, lines);
    const back = JSON.parse(readArtifact(path.join(ctx.artifacts, task.artifact)));
    const ok = a.written === true && b.written === false && c.written === true && back.length === 2
      && back[0].commit === "abc123" && back[0].scheduler === "oc2-eval.timer" && back[1].date !== back[0].date;
    return { ok, detail: ok ? "1 line day one, 2nd line next day" : JSON.stringify({ a: a.written, b: b.written, c: c.written, n: back.length }) };
  },

  "cleanup-stale": async (task, ctx) => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), "eval-clean-"));
    const now = Date.UTC(2026, 10, 4, 12, 0, 0);
    const mk = (id, startMs, withExit) => {
      const d = path.join(root, "runs", id);
      fs.mkdirSync(d, { recursive: true });
      fs.writeFileSync(path.join(d, "start.json"), JSON.stringify({ startedAt: new Date(startMs).toISOString() }));
      const lines = [{ ts: new Date(startMs).toISOString(), run: id, event: "spawn" }];
      if (withExit) lines.push({ ts: new Date(startMs + 1000).toISOString(), run: id, event: "exit", code: 0 });
      fs.writeFileSync(path.join(d, "ledger.jsonl"), lines.map((l) => JSON.stringify(l)).join("\n") + "\n");
    };
    mk("run-old", now - 2 * 86400 * 1000, false);
    mk("run-fresh", now - 3600 * 1000, false);
    const out = cleanupStaleRuns({ root, now });
    const abandoned = path.join(root, "runs", "run-old", "abandoned.json");
    const summary = {
      marked: out.marked.map((m) => m.run),
      freshAbandoned: fs.existsSync(path.join(root, "runs", "run-fresh", "abandoned.json")),
      abandoned: fs.existsSync(abandoned) ? JSON.parse(fs.readFileSync(abandoned, "utf8")) : null,
    };
    writeArtifact(ctx.artifacts, task.artifact, summary);
    const back = JSON.parse(readArtifact(path.join(ctx.artifacts, task.artifact)));
    const ok = back.marked.length === 1 && back.marked[0] === "run-old"
      && back.freshAbandoned === false && back.abandoned && back.abandoned.reason === "stale-run";
    return { ok, detail: ok ? "run-old abandoned, run-fresh live" : JSON.stringify(back).slice(0, 300) };
  },
};

export async function runEval({ tasksFile = path.join(HERE, "eval_tasks.json"), resultsDir = defaultResultsDir(), only = null } = {}) {
  const defs = loadTasks(tasksFile);
  const list = only ? defs.filter((t) => t.id === only) : defs;
  if (only && list.length === 0) {
    const runId = "eval-" + new Date().toISOString().replace(/[:.]/g, "-");
    return { runId, tasks: [{ id: only, name: only, area: "?", pass: "known task id", ok: false, artifact: null, detail: "unknown task id" }], total: 1, passed: 0, failed: 1, score: 0 };
  }
  const runId = "eval-" + new Date().toISOString().replace(/[:.]/g, "-");
  const artifacts = path.join(resultsDir, runId);
  fs.mkdirSync(artifacts, { recursive: true });
  const ctx = { artifacts, resultsDir, runId };
  const results = [];
  for (const task of list) {
    const check = CHECKS[task.id];
    if (!check) {
      results.push({ ...task, ok: false, artifact: null, detail: "no check implements this task" });
      continue;
    }
    try {
      const { ok, detail } = await check(task, ctx);
      results.push({ ...task, ok: Boolean(ok), artifact: task.artifact, detail });
    } catch (err) {
      results.push({ ...task, ok: false, artifact: task.artifact || null, detail: "threw: " + String((err && err.message) || err).slice(0, 300) });
    }
  }
  const passed = results.filter((r) => r.ok).length;
  const total = results.length;
  return {
    runId, total, passed, failed: total - passed,
    score: total === 0 ? 0 : passed / total,
    tasks: results,
  };
}

export function listResults(resultsDir = defaultResultsDir()) {
  let files = [];
  try {
    files = fs.readdirSync(resultsDir).filter((f) => f.startsWith("eval-") && f.endsWith(".json"))
      .map((f) => path.join(resultsDir, f));
  } catch {
    return [];
  }
  const out = [];
  for (const f of files) {
    try {
      const r = JSON.parse(fs.readFileSync(f, "utf8"));
      if (typeof r.score === "number") out.push({ file: f, ...r });
    } catch { /* a torn record never blocks the gate */ }
  }
  return out.sort((a, b) => (a.ts || 0) - (b.ts || 0));
}

// Regression gate: the score must not drop below the LAST recorded score.
// Returns {applies, ok, last, reason}.
export function gateVerdict(resultsDir, score) {
  const prior = listResults(resultsDir);
  if (prior.length === 0) return { applies: false, ok: true, last: null, reason: "no prior recorded score" };
  const last = prior[prior.length - 1];
  if (score + 1e-9 >= last.score) return { applies: true, ok: true, last, reason: `score ${score} >= last ${last.score}` };
  return { applies: true, ok: false, last, reason: `REGRESSION: score ${score} < last recorded ${last.score} (${last.runId})` };
}

export function last10Table(resultsDir = defaultResultsDir()) {
  const rows = listResults(resultsDir).slice(-10).reverse();
  const header = ["iso", "score", "passed", "commit", "runId"];
  const lines = [header];
  for (const r of rows) {
    lines.push([
      r.iso || "-",
      (r.score * 100).toFixed(1) + "%",
      r.passed + "/" + r.total,
      String(r.commit || "unknown").slice(0, 8),
      r.runId || path.basename(r.file),
    ]);
  }
  const widths = header.map((_, i) => Math.max(...lines.map((l) => String(l[i]).length)));
  return lines.map((l) => l.map((c, i) => String(c).padEnd(widths[i])).join("  ")).join("\n");
}

function isMainModule(moduleUrl) {
  if (!process.argv[1]) return false;
  try {
    return fs.realpathSync(process.argv[1]) === fs.realpathSync(url.fileURLToPath(moduleUrl));
  } catch {
    return false;
  }
}

if (isMainModule(import.meta.url)) {
  const arg = (name, fallback = null) => {
    const i = process.argv.indexOf(name);
    return i > -1 && process.argv[i + 1] ? process.argv[i + 1] : fallback;
  };
  const resultsDir = path.resolve(arg("--results-dir", defaultResultsDir()));
  if (process.argv.includes("--last10")) {
    console.log(last10Table(resultsDir));
    process.exit(0);
  }
  const run = await runEval({
    tasksFile: path.resolve(arg("--tasks", path.join(HERE, "eval_tasks.json"))),
    resultsDir,
    only: arg("--only"),
  });
  const record = {
    ts: Date.now(), iso: new Date().toISOString(),
    commit: gitCommit(), provider: PROVIDER,
    runId: run.runId, total: run.total, passed: run.passed, failed: run.failed,
    score: run.score, tasks: run.tasks,
  };
  fs.mkdirSync(resultsDir, { recursive: true });
  let gate = { applies: false, ok: true, reason: "gate not requested" };
  if (process.argv.includes("--gate")) gate = gateVerdict(resultsDir, run.score);
  record.gate = gate;
  fs.writeFileSync(path.join(resultsDir, run.runId + ".json"), JSON.stringify(record, null, 2));
  if (process.argv.includes("--json")) {
    console.log(JSON.stringify(record, null, 2));
  } else {
    for (const t of run.tasks) console.log((t.ok ? "PASS" : "FAIL") + "  " + t.id + "  " + t.detail);
    console.log(`${run.passed}/${run.total} passed (score ${(run.score * 100).toFixed(1)}%) -> ${run.runId}.json`);
    if (process.argv.includes("--gate")) console.log("gate: " + gate.reason);
  }
  if (process.argv.includes("--gate") && !gate.ok) process.exit(2);
  if (run.failed > 0) process.exit(1);
  process.exit(0);
}
