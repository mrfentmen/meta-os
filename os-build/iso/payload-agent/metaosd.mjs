// metaosd — the one API between the Meta OS desktop and the agent relay.
//
// Loopback only, zero dependencies, stdlib http. It holds NO policy: it reads
// the relay's own state files and it forwards job submissions to the queue
// service. If the queue refuses, this says so; it never reports a job it did
// not hand over.
//
//   GET  /status              what the relay is doing right now
//   GET  /agents              who can take work (registry.json)
//   GET  /jobs                the board, from the state dir
//   GET  /runs?agent=&limit=  every run, newest first (read-only)
//   GET  /runs/<id>?n=        one run: log tail + result + exit (read-only)
//   GET  /ledger?n=           relay ledger tail (read-only)
//   GET  /ledger?run=<id>&n=  one run's JSONL tail (kept for older consoles)
//   POST /jobs   {agent, orders}   -> agents/submit.mjs writes the job file
//   POST /halt   {agent}      -> touch stop/<agent>.STOP
//   POST /resume {agent}      -> remove stop/<agent>.STOP
//
//   node metaosd.mjs [--port 18940]
import http from "node:http";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { spawn } from "node:child_process";

const PORT = Number(process.argv.includes("--port")
  ? process.argv[process.argv.indexOf("--port") + 1]
  : 18940);

const HOME = os.homedir();
const STATE = process.env.METAOS_AGENT_STATE
  || process.env.XDG_STATE_HOME && path.join(process.env.XDG_STATE_HOME, "oc2-agent")
  || path.join(HOME, ".local/state/oc2-agent");
const QUEUE = process.env.OC2_QUEUE_URL || "http://127.0.0.1:8935";

// The relay runtime is staged at a few different places depending on lane.
// Report which one exists rather than pretending one does.
// agent-layer/stage.sh puts the node runtime at <payload>/agents, so the
// registry is one level below the payload root as well as at it.
const AGENT_CANDIDATES = [
  process.env.METAOS_AGENT_DIR,
  // The login hook and meta-ask.py call the payload METAOS_AGENT_SHARE; the
  // registry sits in its agents/ subdir. Both names resolve here so the three
  // never disagree about where the relay lives.
  process.env.METAOS_AGENT_SHARE && path.join(process.env.METAOS_AGENT_SHARE, "agents"),
  process.env.METAOS_AGENT_SHARE,
  "/usr/share/metaos/agent/agents",
  "/usr/share/metaos/agent",
  path.join(HOME, "meta-os", "agents"),
  path.join(HOME, "meta-os"),
].filter(Boolean);

function findAgentDir() {
  for (const d of AGENT_CANDIDATES) {
    if (d && fs.existsSync(d)) return d;
  }
  return null;
}

function readJson(file) {
  try {
    return JSON.parse(fs.readFileSync(file, "utf8"));
  } catch {
    return null;
  }
}

function readTail(file, n = 20) {
  try {
    const lines = fs.readFileSync(file, "utf8").trim().split("\n").filter(Boolean);
    return lines.slice(-n).map((l) => {
      try { return JSON.parse(l); } catch { return { raw: l }; }
    });
  } catch {
    return [];
  }
}

// Plain text tails (stdout.log / stderr.log): the lines are already timestamped
// and redacted on disk by runtime.mjs. Never truncated to a teaser by the API:
// `n` caps the transfer, `full=1` returns the whole file up to 1 MiB.
function readTextTail(file, n = 200, full = false) {
  try {
    const text = fs.readFileSync(file, "utf8");
    if (full) return { lines: text.slice(0, 1024 * 1024).split("\n"), truncated: text.length > 1024 * 1024 };
    const lines = text.split("\n");
    if (lines.length && lines[lines.length - 1] === "") lines.pop();
    return { lines: lines.slice(-n), total: lines.length, truncated: lines.length > n };
  } catch {
    return { lines: [], total: 0, truncated: false, missing: true };
  }
}

// The API never returns secrets: orders are person-typed and could contain a
// pasted key, so shape-based redaction applies on the way out. (Run logs are
// already redacted at write time; this covers the fields that are not logs.)
const OUT_SECRET_SHAPES = [
  /sk-[A-Za-z0-9\-_]{8,}/g,
  /gh[pousr]_[A-Za-z0-9]{8,}/g,
  /xox[bpas]-[A-Za-z0-9\-]{8,}/g,
  /Bearer\s+[A-Za-z0-9\-._~+/=]{8,}/g,
];
function redactOut(text) {
  let out = String(text == null ? "" : text);
  for (const [name, value] of Object.entries(process.env)) {
    if (typeof value !== "string" || value.length < 8) continue;
    if (!/(key|token|secret|password|passwd|private|bearer|session|cookie|auth)/i.test(name)) continue;
    if (out.includes(value)) out = out.split(value).join("[REDACTED]");
  }
  for (const re of OUT_SECRET_SHAPES) { re.lastIndex = 0; out = out.replace(re, "[REDACTED]"); }
  return out;
}

const RUN_ID_RE = /^[A-Za-z0-9][A-Za-z0-9._-]*$/;

function runExit(runDir) {
  const meta = readJson(path.join(runDir, "meta.json"));
  if (meta && (meta.exitCode !== null || meta.signal !== null || meta.error || meta.refused)) {
    return { code: meta.exitCode ?? null, signal: meta.signal ?? null, error: meta.error || null, refused: meta.refused || null };
  }
  if (meta && meta.endTime) {
    return { code: meta.exitCode ?? null, signal: meta.signal ?? null, error: meta.error || null, refused: meta.refused || null };
  }
  // Fall back to the ledger when meta.json predates it: the last terminal
  // event is the exit, anything else means the run has not finished.
  const events = readTail(path.join(runDir, "ledger.jsonl"), 500);
  for (let i = events.length - 1; i >= 0; i--) {
    const e = events[i];
    if (!e || typeof e.event !== "string") continue;
    if (e.event === "exit") return { code: e.code ?? null, signal: e.signal ?? null, error: null, refused: null };
    if (e.event === "spawn-error") return { code: null, signal: null, error: String(e.message || "spawn-error"), refused: null };
    if (e.event === "refused") return { code: null, signal: null, error: null, refused: String(e.reason || "refused") };
  }
  return { code: null, signal: null, error: null, refused: null, running: true };
}

function findResultForRun(runId) {
  const dir = path.join(STATE, "jobs");
  let files = [];
  try {
    files = fs.readdirSync(dir).filter((f) => f.endsWith(".result.json"));
  } catch { return null; }
  for (const f of files) {
    const r = readJson(path.join(dir, f));
    if (r && r.run === runId) return { file: f, ...r };
  }
  return null;
}

function listRuns(agent, limit) {
  const dir = path.join(STATE, "runs");
  let entries = [];
  try {
    entries = fs.readdirSync(dir)
      .filter((n) => RUN_ID_RE.test(n))
      .map((n) => {
        try { return { n, mtimeMs: Math.floor(fs.statSync(path.join(dir, n)).mtimeMs) }; }
        catch { return null; }
      })
      .filter(Boolean)
      .sort((a, b) => b.mtimeMs - a.mtimeMs)
      .map((e) => e.n);
  } catch { return []; }
  const rows = [];
  for (const n of entries) {
    const runDir = path.join(dir, n);
    if (!fs.statSync(runDir).isDirectory()) continue;
    const meta = readJson(path.join(runDir, "meta.json"));
    const brief = readJson(path.join(runDir, "brief.json"));
    const name = (meta && meta.agent) || (brief && brief.agent) || null;
    if (agent && name !== agent) continue;
    const exit = runExit(runDir);
    rows.push({
      run: n,
      agent: name,
      orders: brief && typeof brief.orders === "string" ? redactOut(brief.orders).slice(0, 200) : null,
      startTime: (meta && meta.startTime) || null,
      endTime: (meta && meta.endTime) || null,
      durationMs: (meta && meta.durationMs) ?? null,
      exitCode: exit.code, signal: exit.signal, error: exit.error, refused: exit.refused,
      running: exit.running === true,
    });
    if (rows.length >= limit) break;
  }
  return rows;
}

function listJobFiles() {
  const dir = path.join(STATE, "jobs");
  try {
    return fs.readdirSync(dir).sort().map((name) => {
      const st = fs.statSync(path.join(dir, name));
      return { name, size: st.size, mtimeMs: Math.floor(st.mtimeMs) };
    });
  } catch {
    return [];
  }
}

function haltedAgents() {
  const dir = path.join(STATE, "stop");
  try {
    return fs.readdirSync(dir)
      .filter((f) => f.endsWith(".STOP"))
      .map((f) => f.replace(/\.STOP$/, ""));
  } catch {
    return [];
  }
}

function status() {
  const agentDir = findAgentDir();
  const heart = ["watchman-state.json", "heartbeat.json", "health.json"]
    .map((f) => {
      const p = path.join(STATE, f);
      if (!fs.existsSync(p)) return null;
      const st = fs.statSync(p);
      return { file: f, ageSeconds: Math.floor((Date.now() - st.mtimeMs) / 1000), value: readJson(p) };
    })
    .filter(Boolean);
  return {
    v: 1,
    at: new Date().toISOString(),
    stateDir: STATE,
    stateDirExists: fs.existsSync(STATE),
    agentDir,
    agentDirFound: Boolean(agentDir),
    queueUrl: QUEUE,
    halted: haltedAgents(),
    jobFiles: listJobFiles().length,
    heartbeat: heart,
    notices: readTail(path.join(STATE, "notices.jsonl"), 10),
  };
}

function agents() {
  const dir = findAgentDir();
  const reg = dir ? readJson(path.join(dir, "registry.json"))
    : readJson("/opt/face/registry.json");
  if (!reg) return { ok: false, error: "no registry.json found", candidates: AGENT_CANDIDATES };
  const halted = new Set(haltedAgents());
  return {
    ok: true,
    source: path.join(dir || "", "registry.json"),
    agents: (reg.agents || []).map((a) => ({
      name: a.name,
      lane: a.lane || null,
      draft: a.draft === true,
      // B4 — a draft is an explicit refusal, not a silent omission: the reason
      // travels with the entry so the console and meta-ask can quote it.
      draftReason: a.draft === true ? (a.draftReason || "no program yet") : null,
      halted: halted.has(a.name),
      capabilities: a.capabilities || [],
      budget: a.budget || {},
    })),
  };
}

function send(res, code, obj) {
  const body = JSON.stringify(obj, null, 2);
  res.writeHead(code, {
    "Content-Type": "application/json",
    "Content-Length": Buffer.byteLength(body),
    "Cache-Control": "no-store",
  });
  res.end(body);
}

function body(req, limit = 64 * 1024) {
  return new Promise((resolve, reject) => {
    let b = "";
    req.on("data", (c) => {
      b += c;
      if (b.length > limit) { reject(new Error("body too large")); req.destroy(); }
    });
    req.on("end", () => resolve(b));
    req.on("error", reject);
  });
}

// The board is written by agents/submit.mjs as <id>.job.json, and watchman.mjs
// polls exactly those files. The 8935 service is the Trio assessment queue: it
// validates a trio-assessment v1 envelope and refuses an agent job, correctly.
// Prefer the real submission path; fall back to the queue only if it is absent.
function submitScript() {
  const dir = findAgentDir();
  if (!dir) return null;
  const p = path.join(dir, "submit.mjs");
  return fs.existsSync(p) ? p : null;
}

function submitViaScript(script, agent, orders, id) {
  return new Promise((resolve) => {
    const child = spawn("node", [script, "--root", STATE, "--agent", agent, "--orders", orders, "--id", id], {
      stdio: ["ignore", "pipe", "pipe"],
    });
    const chunks = [];
    child.stdout.on("data", (c) => chunks.push(c));
    child.stderr.on("data", (c) => chunks.push(c));
    const timer = setTimeout(() => child.kill("SIGKILL"), 20000);
    child.on("error", (e) => {
      clearTimeout(timer);
      resolve({ ok: false, error: String(e.message || e) });
    });
    child.on("close", (code) => {
      clearTimeout(timer);
      const text = Buffer.concat(chunks).toString().slice(0, 2000);
      resolve({
        ok: code === 0,
        via: script,
        exitCode: code,
        output: text,
      });
    });
  });
}

async function forwardJob(raw) {
  try {
    const r = await fetch(`${QUEUE}/jobs`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: raw,
      signal: AbortSignal.timeout(5000),
    });
    const text = await r.text();
    return { ok: r.ok, forwardedTo: `${QUEUE}/jobs`, status: r.status, response: safeJson(text) };
  } catch (e) {
    // The queue not being up is the common case on a fresh boot; say it plainly.
    return { ok: false, forwardedTo: `${QUEUE}/jobs`, error: String(e.message || e) };
  }
}

function safeJson(t) {
  try { return JSON.parse(t); } catch { return t.slice(0, 2000); }
}

const server = http.createServer(async (req, res) => {
  const remote = req.socket.remoteAddress || "";
  const loopback = remote === "127.0.0.1" || remote === "::1" || remote === "::ffff:127.0.0.1";
  if (!loopback) return send(res, 403, { ok: false, error: "loopback only" });

  const url = new URL(req.url, `http://127.0.0.1:${PORT}`);
  try {
    if (req.method === "GET" && url.pathname === "/status") return send(res, 200, status());
    if (req.method === "GET" && url.pathname === "/agents") return send(res, 200, agents());
    if (req.method === "GET" && url.pathname === "/jobs") {
      return send(res, 200, { ok: true, stateDir: STATE, files: listJobFiles(), halted: haltedAgents() });
    }
    if (req.method === "GET" && url.pathname === "/ledger" && url.searchParams.get("run")) {
      const run = url.searchParams.get("run");
      if (/[^A-Za-z0-9._-]/.test(run)) {
        return send(res, 400, { ok: false, error: "run id required" });
      }
      const n = Math.min(500, Number(url.searchParams.get("n") || 50) || 50);
      const file = path.join(STATE, "runs", run, "ledger.jsonl");
      if (!fs.existsSync(file)) return send(res, 404, { ok: false, error: "no such run", file });
      return send(res, 200, { ok: true, run, file, events: readTail(file, n) });
    }
    if (req.method === "POST" && url.pathname === "/jobs") {
      const raw = await body(req);
      const parsed = safeJson(raw);
      if (!parsed || typeof parsed !== "object" || !parsed.agent || !parsed.orders) {
        return send(res, 400, { ok: false, error: "need {agent, orders}" });
      }
      const script = submitScript();
      if (script) {
        // The id is minted here so the console can link straight to the run:
        // submit.mjs writes exactly this file or refuses loudly, never both.
        const id = "ask-" + Date.now().toString(36) + "-" +
          Math.random().toString(36).slice(2, 6);
        const result = await submitViaScript(script, parsed.agent, parsed.orders, id);
        if (result.ok) {
          return send(res, 200, { ...result, id, agent: parsed.agent });
        }
        return send(res, 502, { ...result, id, agent: parsed.agent });
      }
      const result = await forwardJob(JSON.stringify(parsed));
      return send(res, result.ok ? 200 : 502, result);
    }
    if (req.method === "POST" && url.pathname === "/halt") {
      const parsed = safeJson(await body(req));
      const agent = parsed && parsed.agent;
      if (!agent || /[^A-Za-z0-9._-]/.test(agent)) {
        return send(res, 400, { ok: false, error: "bad agent name" });
      }
      const dir = path.join(STATE, "stop");
      fs.mkdirSync(dir, { recursive: true });
      fs.writeFileSync(path.join(dir, `${agent}.STOP`), "");
      return send(res, 200, { ok: true, halted: agent, file: path.join(dir, `${agent}.STOP`) });
    }
    if (req.method === "POST" && url.pathname === "/resume") {
      const parsed = safeJson(await body(req));
      const agent = parsed && parsed.agent;
      if (!agent || /[^A-Za-z0-9._-]/.test(agent)) {
        return send(res, 400, { ok: false, error: "bad agent name" });
      }
      const file = path.join(STATE, "stop", `${agent}.STOP`);
      try { fs.unlinkSync(file); } catch { /* already resumed: still a success */ }
      return send(res, 200, { ok: true, resumed: agent, halted: false });
    }
    if (req.method === "GET" && url.pathname === "/runs") {
      const agent = url.searchParams.get("agent") || "";
      if (agent && /[^A-Za-z0-9._-]/.test(agent)) {
        return send(res, 400, { ok: false, error: "bad agent name" });
      }
      const limit = Math.min(200, Math.max(1, Number(url.searchParams.get("limit") || 50) || 50));
      return send(res, 200, { ok: true, runs: listRuns(agent, limit) });
    }
    if (req.method === "GET" && url.pathname.startsWith("/runs/")) {
      const run = decodeURIComponent(url.pathname.slice("/runs/".length));
      if (!run || !RUN_ID_RE.test(run)) {
        return send(res, 400, { ok: false, error: "run id required" });
      }
      const runDir = path.join(STATE, "runs", run);
      if (!fs.existsSync(runDir)) return send(res, 404, { ok: false, error: "no such run", run });
      const n = Math.min(5000, Math.max(1, Number(url.searchParams.get("n") || 200) || 200));
      const full = url.searchParams.get("full") === "1";
      const meta = readJson(path.join(runDir, "meta.json"));
      const brief = readJson(path.join(runDir, "brief.json"));
      const exit = runExit(runDir);
      const stdout = readTextTail(path.join(runDir, "stdout.log"), n, full);
      const stderr = readTextTail(path.join(runDir, "stderr.log"), n, full);
      return send(res, 200, {
        ok: true,
        run,
        agent: (meta && meta.agent) || (brief && brief.agent) || null,
        orders: brief && typeof brief.orders === "string" ? redactOut(brief.orders) : null,
        lane: (brief && brief.lane) || null,
        meta: meta || null,
        exit: { code: exit.code, signal: exit.signal, error: exit.error, refused: exit.refused },
        result: findResultForRun(run),
        ledger: readTail(path.join(runDir, "ledger.jsonl"), Math.min(n, 500)),
        stdout, stderr,
      });
    }
    if (req.method === "GET" && url.pathname === "/ledger") {
      const n = Math.min(500, Math.max(1, Number(url.searchParams.get("n") || 50) || 50));
      const file = path.join(STATE, "watchman.jsonl");
      if (!fs.existsSync(file)) return send(res, 404, { ok: false, error: "no relay ledger yet", file });
      return send(res, 200, { ok: true, file, events: readTail(file, n) });
    }
    if (req.method === "GET" && url.pathname === "/healthz") {
      return send(res, 200, { ok: true, pid: process.pid });
    }
    return send(res, 404, { ok: false, error: "not found", path: url.pathname });
  } catch (e) {
    return send(res, 500, { ok: false, error: String(e.message || e) });
  }
});

server.listen(PORT, "127.0.0.1", () => {
  console.log(`metaosd on 127.0.0.1:${PORT} state=${STATE} queue=${QUEUE}`);
});
