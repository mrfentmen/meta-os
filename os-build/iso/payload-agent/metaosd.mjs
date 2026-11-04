// metaosd.mjs — the metaosd agent daemon (R2-T3 lane, Section B).
//
// Listens ONLY on 127.0.0.1:18940 (default; --port overrides for tests).
// File queue under a data dir OUTSIDE the git tree:
//   $METAOS_STATE/metaosd   (when METAOS_STATE is set)
//   ~/.local/state/metaos/metaosd   (otherwise; --data overrides both)
// Node stdlib only. No model calls: the built-in executor runs a local
// stub child (zero network); --dry-run / "dry-run":true spawns nothing.
//
// Endpoints (all JSON unless noted):
//   GET  /health                       liveness + queue depth + oldest age + pool state
//   POST /jobs                        submit {id?,agent,input?,budget?,timeout?,"dry-run"?}
//                                       Idempotency-Key header supported; unknown fields refused by name
//   GET  /jobs?agent=&status=&since=&until=   list + filter
//   GET  /jobs/:id                     full run record
//   GET  /jobs/:id/status[?waitMs=N]   poll contract (long-poll up to N ms for a change)
//   GET  /jobs/:id/events              SSE stream of status snapshots (dies with the client only)
//   POST /jobs/:id/cancel              cancel queued/running job; record stays as cancelled
//   POST /jobs/:id/retry               manual retry (terminal jobs, within maxAttempts)
//   GET  /jobs/:id/receipt             the job's HMAC receipt
//   GET  /verify?job=ID                verify one receipt (refuses without key, naming its path)
//
// Offline (no daemon) commands:
//   node metaosd.mjs verify --data DIR --job ID
//   node metaosd.mjs verify-chain --data DIR
//
// Job shape is defined ONCE in agents/job.schema.json and read here at
// runtime (never duplicated). Retry policy lives inside budget
// {maxAttempts, backoffMs} so the top level stays exactly the six
// schema fields.

import { spawn } from "node:child_process";
import crypto from "node:crypto";
import fs from "node:fs";
import http from "node:http";
import os from "node:os";
import path from "node:path";
import url from "node:url";

import {
  appendChain,
  atomicWrite,
  chainPrev,
  checkWritable,
  cleanStaleLock,
  dataPaths,
  defaultDataDir,
  ensureDataDir,
  jobFile,
  listJobs,
  loadIdem,
  loadJob,
  loadOrCreateKey,
  loadSchema,
  readKey,
  receiptHmac,
  releaseLock,
  saveIdem,
  saveJob,
  schemaPath,
  takeLock,
  validateAgainstSchema,
  verifyReceiptObject,
} from "../../../server/queue/metaosd_store.mjs";

const HERE = path.dirname(url.fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, "..", "..", "..");
const VERSION = "0.1.0-r2t3";
const HOST = "127.0.0.1"; // loopback only: never 0.0.0.0 (task 25 / bind proof)
const DEFAULT_PORT = 18940;

export const STATUSES = ["queued", "running", "succeeded", "failed", "timeout", "cancelled", "dryrun"];

// Local stub child: zero network, zero model. Reads METAOSD_JOB
// {id, agent, input}; input may carry {sleepMs, exitCode, artifact:{name,content}}.
const STUB_SRC = `
const fs = require("fs");
const job = JSON.parse(process.env.METAOSD_JOB || "{}");
const input = (job && job.input && typeof job.input === "object") ? job.input : {};
const sleep = Math.max(0, Number(input.sleepMs || 0));
const code = Number.isInteger(input.exitCode) ? input.exitCode : 0;
if (input.artifact && input.artifact.name) {
  fs.writeFileSync(String(input.artifact.name), String(input.artifact.content || ""));
}
console.log("metaosd-stub agent=" + job.agent + " job=" + job.id);
setTimeout(() => { console.log("metaosd-stub done code=" + code); process.exit(code); }, sleep);
`;

function log(...args) {
  console.error("metaosd:", ...args);
}

function parseArgs(argv) {
  const out = { cmd: "serve" };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "verify" || a === "verify-chain") out.cmd = a;
    else if (a === "--port") out.port = Number(argv[++i]);
    else if (a === "--data") out.data = argv[++i];
    else if (a === "--workers") out.workers = Number(argv[++i]);
    else if (a === "--agent-cap") out.agentCap = Number(argv[++i]);
    else if (a === "--job") out.job = argv[++i];
    else if (a === "--help" || a === "-h") out.cmd = "help";
  }
  return out;
}

function resolveCommands() {
  // Production payloads may map agents to real commands via a JSON file
  // { "<agent>": ["argv0", ...] }. Default (and all tests): local stub.
  const file = process.env.METAOSD_CMDS_FILE;
  if (!file) return {};
  try {
    const m = JSON.parse(fs.readFileSync(file, "utf8"));
    if (m && typeof m === "object") return m;
  } catch (e) {
    log("WARN ignoring METAOSD_CMDS_FILE " + file + ": " + (e && e.message));
  }
  return {};
}

export function makeId() {
  return "job-" + Date.now().toString(36) + "-" + crypto.randomBytes(4).toString("hex");
}

function nowIso() {
  return new Date().toISOString();
}

export function createDaemon(opts = {}) {
  const dataDir = opts.dataDir;
  const poolSize = opts.poolSize || 2;
  const agentCap = opts.agentCap || 1;
  const schemaFile = opts.schemaFile;
  const { schema } = loadSchema(schemaFile);
  const cmds = resolveCommands();
  ensureDataDir(dataDir);

  const jobs = new Map(); // id -> record (mirrors jobs/*.json)
  for (const rec of listJobs(dataDir)) jobs.set(rec.id, rec);
  const idem = loadIdem(dataDir);
  const running = new Map(); // id -> { child, timer, killedFor }
  const listeners = new Map(); // id -> Set<fn(record)>
  let closed = false;
  let saveChain = Promise.resolve();

  function persist(rec) {
    if (closed) return; // teardown won the race: drop late writes
    rec.updatedAt = nowIso();
    saveJob(dataDir, rec);
    jobs.set(rec.id, rec);
    const set = listeners.get(rec.id);
    if (set) for (const fn of [...set]) { try { fn(rec); } catch { /* listener-side */ } }
  }

  function onChange(id, fn) {
    if (!listeners.has(id)) listeners.set(id, new Set());
    listeners.get(id).add(fn);
    return () => { const s = listeners.get(id); if (s) s.delete(fn); };
  }

  function activeFor(agent) {
    let n = 0;
    for (const rec of jobs.values()) {
      if (rec.status === "running" && rec.agent === agent) n++;
    }
    return n;
  }

  function busyIds() {
    return [...jobs.values()].filter((r) => r.status === "running").map((r) => r.id);
  }

  function perAgent() {
    const m = {};
    for (const r of jobs.values()) {
      if (r.status === "running") m[r.agent] = (m[r.agent] || 0) + 1;
    }
    return m;
  }

  function runDir(id) {
    const d = path.join(dataPaths(dataDir).runs, id);
    fs.mkdirSync(d, { recursive: true });
    return d;
  }

  function finishReceipt(rec) {
    // One receipt per terminal run, HMAC-chained (prev = last chain hmac).
    const { key: rkey } = loadOrCreateKey(dataDir);
    const fields = {
      job: rec.id,
      agent: rec.agent,
      run: "runs/" + rec.id,
      status: rec.status,
      attempts: rec.attempts.length,
      startedAt: rec.startedAt,
      endedAt: rec.endedAt,
      exit: rec.exit,
      spawned: rec.spawned,
      artifacts: rec.artifacts,
      prev: chainPrev(dataDir),
    };
    const hmac = receiptHmac(rkey, fields);
    const receipt = { ...fields, hmac };
    atomicWrite(path.join(runDir(rec.id), "receipt.json"), JSON.stringify(receipt, null, 2) + "\n");
    appendChain(dataDir, receipt);
    rec.receipt = receipt.hmac;
    return receipt;
  }

  function scanArtifacts(rec) {
    // Artifact paths are RELATIVE to the run dir (runs/<id>/); the
    // absolute base is the data dir, which lives outside the git tree.
    try {
      return fs.readdirSync(runDir(rec.id))
        .filter((n) => n !== "receipt.json" && !n.endsWith(".tmp-" + process.pid) && !n.includes(".tmp-"))
        .sort();
    } catch {
      return [];
    }
  }

  function terminal(rec, status, exit) {
    rec.status = status;
    rec.exit = exit;
    rec.endedAt = nowIso();
    rec.retry = null;
    rec.artifacts = scanArtifacts(rec);
    finishReceipt(rec);
    persist(rec);
  }

  function maybeRetry(rec, failedStatus, exit) {
    const maxAttempts = (rec.budget && Number.isInteger(rec.budget.maxAttempts) && rec.budget.maxAttempts >= 1)
      ? rec.budget.maxAttempts : 1;
    const base = (rec.budget && Number(rec.budget.backoffMs) > 0) ? Number(rec.budget.backoffMs) : 0;
    if (rec.attempts.length < maxAttempts) {
      const wait = base * Math.pow(2, rec.attempts.length - 1);
      rec.status = "queued";
      rec.exit = exit;
      rec.nextRunAt = new Date(Date.now() + wait).toISOString();
      rec.retry = { nextAttempt: rec.attempts.length + 1, backoffMs: wait, at: rec.nextRunAt };
      persist(rec);
      pumpSoon();
      return true;
    }
    terminal(rec, failedStatus, exit);
    return false;
  }

  function launch(rec) {
    const attemptN = rec.attempts.length + 1;
    const attempt = { n: attemptN, startedAt: nowIso(), backoffWaitedMs: rec.retry ? rec.retry.backoffMs : 0 };
    rec.attempts.push(attempt);
    rec.status = "running";
    rec.retry = null;
    rec.nextRunAt = null;
    if (!rec.startedAt) rec.startedAt = attempt.startedAt;
    persist(rec);

    const dir = runDir(rec.id);
    const outFile = path.join(dir, "output-attempt" + attemptN + ".log");
    let argv;
    if (cmds[rec.agent]) {
      argv = cmds[rec.agent];
    } else {
      argv = [process.execPath, "-e", STUB_SRC];
    }
    rec.spawned = true;
    rec.command = argv[0] === process.execPath ? ["node", "-e", "<stub>"] : argv;
    persist(rec);

    const out = fs.createWriteStream(outFile);
    const child = spawn(argv[0], argv.slice(1), {
      cwd: dir,
      env: { ...process.env, METAOSD_JOB: JSON.stringify({ id: rec.id, agent: rec.agent, input: rec.input }) },
      stdio: ["ignore", "pipe", "pipe"],
    });
    child.stdout.pipe(out);
    child.stderr.pipe(out);
    const state = { child, timer: null, timedOut: false, cancel: false };
    running.set(rec.id, state);

    const timeoutMs = Number(rec.timeout) > 0 ? Number(rec.timeout) : 0;
    if (timeoutMs > 0) {
      state.timer = setTimeout(() => {
        state.timedOut = true;
        attempt.timeoutMs = timeoutMs;
        try { child.kill("SIGTERM"); } catch { /* already gone */ }
        state.hardTimer = setTimeout(() => { try { child.kill("SIGKILL"); } catch { /* gone */ } }, 800);
      }, timeoutMs);
      if (state.timer.unref) state.timer.unref();
    }

    child.on("exit", (code, signal) => {
      if (closed) return;
      if (state.timer) clearTimeout(state.timer);
      if (state.hardTimer) clearTimeout(state.hardTimer);
      running.delete(rec.id);
      attempt.endedAt = nowIso();
      attempt.exit = code;
      attempt.signal = signal;
      if (state.cancel) {
        attempt.state = "cancelled";
        terminal(rec, "cancelled", { code, signal });
      } else if (state.timedOut) {
        attempt.state = "timeout";
        maybeRetry(rec, "timeout", { code, signal, timeoutMs });
      } else if (code === 0) {
        attempt.state = "succeeded";
        terminal(rec, "succeeded", { code, signal });
      } else {
        attempt.state = "failed";
        maybeRetry(rec, "failed", { code, signal });
      }
      pumpSoon();
    });
    child.on("error", (err) => {
      if (closed) return;
      if (state.timer) clearTimeout(state.timer);
      running.delete(rec.id);
      attempt.endedAt = nowIso();
      attempt.state = "failed";
      attempt.error = String((err && err.message) || err);
      maybeRetry(rec, "failed", { code: null, spawnError: attempt.error });
      pumpSoon();
    });
  }

  let pumpTimer = null;
  function pumpSoon() {
    if (pumpTimer) return;
    pumpTimer = setTimeout(() => { pumpTimer = null; pump(); }, 25);
    if (pumpTimer.unref) pumpTimer.unref();
  }

  function pump() {
    const active = busyIds().length;
    if (active >= poolSize) return;
    const queued = [...jobs.values()]
      .filter((r) => r.status === "queued" && (!r.nextRunAt || r.nextRunAt <= nowIso()))
      .sort((a, b) => (a.submittedAt < b.submittedAt ? -1 : 1));
    let slots = poolSize - active;
    for (const rec of queued) {
      if (slots <= 0) break;
      if (activeFor(rec.agent) >= agentCap) continue; // per-agent cap: named refusal lives in submit path; running jobs wait
      slots--;
      launch(rec);
    }
    // Wake for the earliest future backoff.
    const future = [...jobs.values()]
      .filter((r) => r.status === "queued" && r.nextRunAt && r.nextRunAt > nowIso())
      .sort((a, b) => (a.nextRunAt < b.nextRunAt ? -1 : 1))[0];
    if (future) {
      const ms = Math.max(0, new Date(future.nextRunAt).getTime() - Date.now());
      setTimeout(() => pump(), Math.min(ms, 30000));
    }
  }
  const pumpIv = setInterval(pump, 200);
  if (pumpIv.unref) pumpIv.unref();

  function shutdown() {
    closed = true;
    if (pumpTimer) clearTimeout(pumpTimer);
    clearInterval(pumpIv);
    for (const [, st] of running) {
      if (st.timer) clearTimeout(st.timer);
      if (st.hardTimer) clearTimeout(st.hardTimer);
      try { st.child.kill("SIGKILL"); } catch { /* gone */ }
    }
    running.clear();
    listeners.clear();
  }

  function submit(body, requestKey) {
    const v = validateAgainstSchema(body, schema);
    if (!v.ok) return { status: 400, body: { error: "refused job: " + v.errors.join("; "), errors: v.errors } };
    if (requestKey) {
      const hit = idem[requestKey];
      if (hit && jobs.has(hit)) {
        return { status: 200, body: { id: hit, existing: true } };
      }
    }
    const id = typeof body.id === "string" ? body.id : makeId();
    if (jobs.has(id)) {
      return { status: 409, body: { error: "job already exists: " + id } };
    }
    // Per-agent concurrency cap is enforced with a NAMED refusal (task 36).
    if (activeFor(body.agent) >= agentCap) {
      return {
        status: 429,
        body: { error: "agent-concurrency-cap: agent \"" + body.agent + "\" already runs " + agentCap + " job(s)", agent: body.agent, cap: agentCap },
      };
    }
    const rec = {
      id,
      agent: body.agent,
      input: body.input === undefined ? {} : body.input,
      budget: body.budget === undefined ? {} : body.budget,
      timeout: body.timeout === undefined ? 0 : body.timeout,
      dryRun: body["dry-run"] === true,
      status: "queued",
      attempts: [],
      exit: null,
      spawned: false,
      command: null,
      artifacts: [],
      artifactsRelativeTo: "runs/" + id,
      submittedAt: nowIso(),
      startedAt: null,
      endedAt: null,
      updatedAt: nowIso(),
      nextRunAt: null,
      retry: null,
      receipt: null,
    };
    if (requestKey && !idem[requestKey]) {
      idem[requestKey] = id;
      saveIdem(dataDir, idem);
    }
    if (rec.dryRun) {
      // Dry run: validate + record, spawn nothing, contact no model.
      rec.spawned = false;
      rec.command = null;
      rec.status = "dryrun";
      rec.startedAt = nowIso();
      rec.endedAt = rec.startedAt;
      rec.artifacts = ["record.json"];
      atomicWrite(path.join(runDir(id), "record.json"), JSON.stringify(rec, null, 2) + "\n");
      finishReceipt(rec);
      persist(rec);
      return { status: 201, body: { id, dryRun: true } };
    }
    persist(rec);
    pumpSoon();
    return { status: 201, body: { id } };
  }

  function cancel(id) {
    const rec = jobs.get(id);
    if (!rec) return { status: 404, body: { error: "no such job: " + id } };
    if (rec.status === "queued") {
      rec.attempts.push({ n: rec.attempts.length + 1, startedAt: null, endedAt: nowIso(), state: "cancelled", note: "cancelled while queued" });
      terminal(rec, "cancelled", { code: null, signal: null });
      return { status: 200, body: { id, status: "cancelled" } };
    }
    if (rec.status === "running") {
      const st = running.get(id);
      if (st) {
        st.cancel = true;
        try { st.child.kill("SIGTERM"); } catch { /* gone */ }
        setTimeout(() => { try { st.child.kill("SIGKILL"); } catch { /* gone */ } }, 800).unref?.();
      }
      return { status: 200, body: { id, status: "cancelling" } };
    }
    return { status: 409, body: { error: "job " + id + " is already " + rec.status + "; nothing to cancel" } };
  }

  function retry(id) {
    const rec = jobs.get(id);
    if (!rec) return { status: 404, body: { error: "no such job: " + id } };
    if (!["failed", "timeout", "cancelled"].includes(rec.status)) {
      return { status: 409, body: { error: "job " + id + " is " + rec.status + "; only failed/timeout/cancelled jobs can be retried" } };
    }
    const maxAttempts = (rec.budget && Number.isInteger(rec.budget.maxAttempts) && rec.budget.maxAttempts >= 1)
      ? rec.budget.maxAttempts : 1;
    if (rec.attempts.length >= maxAttempts) {
      return { status: 409, body: { error: "job " + id + " exhausted maxAttempts=" + maxAttempts, maxAttempts } };
    }
    const base = (rec.budget && Number(rec.budget.backoffMs) > 0) ? Number(rec.budget.backoffMs) : 0;
    const wait = base * Math.pow(2, rec.attempts.length - 1);
    rec.status = "queued";
    rec.exit = null;
    rec.endedAt = null;
    rec.nextRunAt = new Date(Date.now() + wait).toISOString();
    rec.retry = { nextAttempt: rec.attempts.length + 1, backoffMs: wait, at: rec.nextRunAt, manual: true };
    persist(rec);
    pumpSoon();
    return { status: 200, body: { id, status: "queued", backoffMs: wait } };
  }

  return {
    jobs, submit, cancel, retry, onChange, pump, shutdown,
    get(id) { return jobs.get(id) || null; },
    list(filters = {}) {
      let out = [...jobs.values()].sort((a, b) => (a.submittedAt < b.submittedAt ? -1 : 1));
      if (filters.agent) out = out.filter((r) => r.agent === filters.agent);
      if (filters.status) out = out.filter((r) => r.status === filters.status);
      if (filters.since) out = out.filter((r) => r.submittedAt >= filters.since);
      if (filters.until) out = out.filter((r) => r.submittedAt <= filters.until);
      return out;
    },
    snapshot(id) {
      const r = jobs.get(id);
      if (!r) return null;
      return {
        id: r.id, agent: r.agent, status: r.status,
        attempt: r.attempts.length, attempts: r.attempts,
        startedAt: r.startedAt, endedAt: r.endedAt, exit: r.exit,
        spawned: r.spawned, command: r.command,
        artifacts: r.artifacts, artifactsRelativeTo: r.artifactsRelativeTo,
        retry: r.retry, receipt: r.receipt, updatedAt: r.updatedAt,
        restarted: r.restarted === true,
      };
    },
    queueDepth() { return [...jobs.values()].filter((r) => r.status === "queued").length; },
    oldestJobAgeMs() {
      const q = [...jobs.values()].filter((r) => r.status === "queued");
      if (q.length === 0) return null;
      const oldest = q.reduce((a, b) => (a.submittedAt < b.submittedAt ? a : b));
      return Date.now() - new Date(oldest.submittedAt).getTime();
    },
    busyIds, perAgent, poolSize, agentCap, dataDir, schema,
  };
}

// ---- HTTP ----
function send(res, code, obj) {
  const body = Buffer.from(JSON.stringify(obj));
  res.writeHead(code, { "Content-Type": "application/json", "Content-Length": body.length });
  res.end(body);
}

function readBody(req, limit = 1 << 20) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    let size = 0;
    req.on("data", (c) => {
      size += c.length;
      if (size > limit) {
        reject(new Error("body too large"));
        req.destroy();
        return;
      }
      chunks.push(c);
    });
    req.on("end", () => resolve(Buffer.concat(chunks).toString("utf8")));
    req.on("error", reject);
    // Client disconnect mid-upload must not kill the daemon or any job:
    // the request is simply abandoned here; running jobs are detached.
    req.on("close", () => resolve(null));
  });
}

export function createServer(daemon, opts = {}) {
  const startedAt = Date.now();
  const server = http.createServer(async (req, res) => {
    try {
      const u = new URL(req.url || "/", "http://" + HOST);
      const p = u.pathname;
      if (req.method === "GET" && p === "/health") {
        const w = checkWritable(daemon.dataDir);
        send(res, 200, {
          ok: true,
          service: "metaosd",
          version: VERSION,
          host: HOST,
          port: opts.port || DEFAULT_PORT,
          dataDir: daemon.dataDir,
          writable: w.ok,
          uptimeMs: Date.now() - startedAt,
          queueDepth: daemon.queueDepth(),
          oldestJobAgeMs: daemon.oldestJobAgeMs(),
          workers: { size: daemon.poolSize, busy: daemon.busyIds(), perAgent: daemon.perAgent() },
          agentCap: daemon.agentCap,
          store: "file",
          receiptKey: readKey(daemon.dataDir).key != null,
        });
        return;
      }
      if (req.method === "POST" && p === "/jobs") {
        const raw = await readBody(req);
        if (raw == null) return; // client went away; nothing to answer, job flow untouched
        let body;
        try {
          body = JSON.parse(raw || "{}");
        } catch {
          send(res, 400, { error: "request body is not JSON" });
          return;
        }
        const requestKey = req.headers["idempotency-key"] || null;
        const out = daemon.submit(body, typeof requestKey === "string" ? requestKey : null);
        send(res, out.status, out.body);
        return;
      }
      if (req.method === "GET" && p === "/jobs") {
        const since = u.searchParams.get("since");
        const until = u.searchParams.get("until");
        for (const [name, v] of [["since", since], ["until", until]]) {
          if (v != null && Number.isNaN(new Date(v).getTime())) {
            send(res, 400, { error: "bad ?" + name + " date: " + JSON.stringify(v) });
            return;
          }
        }
        const rows = daemon.list({
          agent: u.searchParams.get("agent") || undefined,
          status: u.searchParams.get("status") || undefined,
          since: since || undefined,
          until: until || undefined,
        });
        send(res, 200, { jobs: rows.map((r) => daemon.snapshot(r.id)), count: rows.length });
        return;
      }
      const m = p.match(/^\/jobs\/([^/]+)(\/(status|events|receipt|cancel|retry))?$/);
      if (m) {
        const id = decodeURIComponent(m[1]);
        const sub = m[2] || "";
        if (sub === "/cancel" && req.method === "POST") {
          const out = daemon.cancel(id);
          send(res, out.status, out.body);
          return;
        }
        if (sub === "/retry" && req.method === "POST") {
          const out = daemon.retry(id);
          send(res, out.status, out.body);
          return;
        }
        if ((sub === "" || sub === "/status") && req.method === "GET") {
          const snap = daemon.snapshot(id);
          if (!snap) { send(res, 404, { error: "no such job: " + id }); return; }
          const waitMs = Math.max(0, Math.min(30000, Number(u.searchParams.get("waitMs") || 0)));
          if (!waitMs || sub === "") { send(res, 200, snap); return; }
          // Long-poll: answer when the record changes, else the same snapshot.
          const seen = snap.updatedAt;
          const done = await new Promise((resolve) => {
            const t = setTimeout(() => { off(); resolve(daemon.snapshot(id)); }, waitMs);
            const off = daemon.onChange(id, (rec) => {
              if (rec.updatedAt !== seen) { clearTimeout(t); off(); resolve(daemon.snapshot(id)); }
            });
          });
          send(res, 200, done);
          return;
        }
        if (sub === "/events" && req.method === "GET") {
          const snap = daemon.snapshot(id);
          if (!snap) { send(res, 404, { error: "no such job: " + id }); return; }
          res.writeHead(200, {
            "Content-Type": "text/event-stream",
            "Cache-Control": "no-cache",
            Connection: "keep-alive",
          });
          res.write("data: " + JSON.stringify(snap) + "\n\n");
          const off = daemon.onChange(id, (rec) => {
            try { res.write("data: " + JSON.stringify(daemon.snapshot(id)) + "\n\n"); } catch { /* gone */ }
          });
          // A dropped SSE client only ends its own stream; the job is detached.
          req.on("close", () => { off(); try { res.end(); } catch { /* gone */ } });
          return;
        }
        if (sub === "/receipt" && req.method === "GET") {
          const rec = daemon.get(id);
          if (!rec) { send(res, 404, { error: "no such job: " + id }); return; }
          try {
            const receipt = JSON.parse(fs.readFileSync(
              path.join(dataPaths(daemon.dataDir).runs, id, "receipt.json"), "utf8"));
            send(res, 200, receipt);
          } catch {
            send(res, 404, { error: "no receipt yet for job " + id });
          }
          return;
        }
      }
      if (req.method === "GET" && p === "/verify") {
        const id = u.searchParams.get("job");
        if (!id) { send(res, 400, { error: "missing ?job= id" }); return; }
        const { key, path: keyPath } = readKey(daemon.dataDir);
        if (!key) {
          send(res, 400, { error: "refusing to verify without a receipt key: no receipt key at " + keyPath, keyPath });
          return;
        }
        let receipt;
        try {
          receipt = JSON.parse(fs.readFileSync(
            path.join(dataPaths(daemon.dataDir).runs, id, "receipt.json"), "utf8"));
        } catch {
          send(res, 404, { error: "no receipt yet for job " + id });
          return;
        }
        const v = verifyReceiptObject(key, receipt, null);
        send(res, v.ok ? 200 : 409, v.ok ? { ok: true, job: id, hmac: receipt.hmac } : { ok: false, job: id, error: v.error });
        return;
      }
      send(res, 404, { error: "not found" });
    } catch (e) {
      try { send(res, 500, { error: String((e && e.message) || e) }); } catch { /* gone */ }
    }
  });
  return server;
}

// ---- serve ----
export async function serve(args) {
  const port = args.port || Number(process.env.METAOSD_PORT) || DEFAULT_PORT;
  const dataDir = args.data || process.env.METAOSD_DATA || defaultDataDir();
  const poolSize = args.workers || Number(process.env.METAOSD_WORKERS) || 2;
  const agentCap = args.agentCap || Number(process.env.METAOSD_AGENT_CAP) || 1;

  // Task 45: refuse to start when the data dir is not writable, naming it.
  const w = checkWritable(dataDir);
  if (!w.ok) {
    console.error("metaosd: refusing to start: data dir not writable: " + dataDir + " (" + w.error + ")");
    process.exit(2);
  }
  ensureDataDir(dataDir);

  // Task 46: clean stale locks on start, logging what was removed.
  let removed = null;
  try {
    removed = takeLock(dataDir);
  } catch (e) {
    console.error("metaosd: " + ((e && e.message) || e));
    process.exit(2);
  }
  if (removed) {
    log("removed stale lock " + removed.path + " (pid " + removed.pid + " not running, startedAt " + removed.startedAt + ")");
  }

  const schemaFile = process.env.METAOSD_SCHEMA || schemaPath(process.env.METAOSD_CHECKOUT || ROOT);
  let daemon;
  try {
    daemon = createDaemon({ dataDir, poolSize, agentCap, schemaFile });
  } catch (e) {
    console.error("metaosd: " + ((e && e.message) || e));
    releaseLock(dataDir);
    process.exit(2);
  }

  // Restart recovery: jobs left running by a dead daemon go back to queued
  // (attempts preserved); queued jobs stay queued. Durable queue = files.
  let requeued = 0;
  for (const rec of daemon.jobs.values()) {
    if (rec.status === "running") {
      const last = rec.attempts[rec.attempts.length - 1];
      if (last && !last.state) {
        last.state = "orphaned";
        last.note = "daemon died mid-attempt; requeued on restart";
        last.endedAt = nowIso();
      }
      rec.status = "queued";
      rec.nextRunAt = null;
      rec.retry = null;
      rec.restarted = true;
      saveJob(dataDir, rec);
      requeued++;
    }
  }

  const server = createServer(daemon, { port });
  server.listen(port, HOST, () => {
    log("listening on " + HOST + ":" + port + " dataDir=" + dataDir +
      " workers=" + poolSize + " agentCap=" + agentCap +
      " jobs=" + daemon.jobs.size + " requeued=" + requeued);
  });
  const shutdown = () => {
    // Running jobs are re-queued on next start; just unlock and exit.
    // (kill -9 skips this: the stale lock + running records are the
    // recovery path, proven in R2_T3_B.md.)
    releaseLock(dataDir);
    server.close(() => process.exit(0));
    setTimeout(() => process.exit(0), 1500).unref();
  };
  process.on("SIGTERM", shutdown);
  process.on("SIGINT", shutdown);
}

// ---- offline verify (no daemon; "one command" in R2_T3_B.md) ----
export async function offlineVerify(args) {
  const dataDir = args.data || process.env.METAOSD_DATA || defaultDataDir();
  const { verifyChain, readKey: rk, dataPaths: dp, verifyReceiptObject: vro } = await import("../../../server/queue/metaosd_store.mjs");
  if (args.cmd === "verify-chain") {
    const v = verifyChain(dataDir);
    if (v.ok) {
      console.log("verify-chain: OK, " + v.checked + " receipt(s) chained under " + dataDir);
      return 0;
    }
    console.error("verify-chain: FAIL: " + v.error);
    return 1;
  }
  if (!args.job) {
    console.error("usage: metaosd.mjs verify --data DIR --job ID");
    return 2;
  }
  const { key, path: keyPath } = rk(dataDir);
  if (!key) {
    console.error("metaosd: refusing to verify without a receipt key: no receipt key at " + keyPath);
    return 2;
  }
  let receipt;
  try {
    receipt = JSON.parse(fs.readFileSync(path.join(dp(dataDir).runs, args.job, "receipt.json"), "utf8"));
  } catch {
    console.error("metaosd: no receipt yet for job " + args.job);
    return 1;
  }
  const v = vro(key, receipt, null);
  if (v.ok) {
    console.log("verify: OK job=" + args.job + " hmac=" + receipt.hmac);
    return 0;
  }
  console.error("verify: FAIL job=" + args.job + ": " + v.error);
  return 1;
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
  const args = parseArgs(process.argv.slice(2));
  if (args.cmd === "help") {
    console.log("usage: metaosd.mjs [--port 18940] [--data DIR] [--workers N] [--agent-cap N]");
    console.log("       metaosd.mjs verify --data DIR --job ID");
    console.log("       metaosd.mjs verify-chain --data DIR");
    process.exit(0);
  } else if (args.cmd === "verify" || args.cmd === "verify-chain") {
    process.exit(await offlineVerify(args));
  } else {
    await serve(args);
  }
}
