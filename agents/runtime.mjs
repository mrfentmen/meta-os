// Meta OS agent layer — host runtime, slice 1 (AGENT_LAYER_SPEC.md).
// Real spawn/kill, STOP file, budgets, watch poll/compare, and an
// append-only JSONL ledger per run. Zero dependencies.
//   node agents/runtime.mjs list            (registry entries)
//   node agents/runtime.mjs spawn <name>    (run one agent)
//   node agents/runtime.mjs watch <name>    (watch its targets)
import { spawn } from "node:child_process";
import { lessons } from "./lessons.mjs";
import fs from "node:fs";
import path from "node:path";
import url from "node:url";

export function loadRegistry(file) {
  const raw = JSON.parse(fs.readFileSync(file, "utf8"));
  if (!Array.isArray(raw.agents)) throw new Error("registry: 'agents' must be an array");
  const seen = new Set();
  for (const a of raw.agents) {
    if (!a.name || typeof a.name !== "string") throw new Error("registry: agent missing name");
    if (seen.has(a.name)) throw new Error("registry: duplicate agent " + a.name);
    seen.add(a.name);
    if (!Array.isArray(a.command) || a.command.length === 0) throw new Error("registry: " + a.name + " missing command");
    a.budget = a.budget || {};
    if (a.budget.maxWallMs != null && !(a.budget.maxWallMs > 0)) throw new Error("registry: " + a.name + " bad maxWallMs");
  }
  return raw.agents;
}

export class Ledger {
  constructor(file) { this.file = file; }
  add(run, event, fields = {}) {
    const line = JSON.stringify({ ts: new Date().toISOString(), run, event, ...fields }) + "\n";
    fs.appendFileSync(this.file, line);
    return line;
  }
  read() {
    if (!fs.existsSync(this.file)) return [];
    return fs.readFileSync(this.file, "utf8").split("\n").filter(Boolean).map((l) => JSON.parse(l));
  }
}

export function spawnAgent(agent, { root, job = {} } = {}) {
  const runId = agent.name + "-" + Date.now().toString(36);
  const runDir = path.join(root, "runs", runId);
  fs.mkdirSync(runDir, { recursive: true });
  const ledger = new Ledger(path.join(runDir, "ledger.jsonl"));
  // The assembled brief lands BEFORE the agent starts (spec S4):
  // it opens its eyes already briefed.
  const brief = {
    agent: agent.name, lane: agent.lane || null, run: runId,
    orders: job.orders || "", budget: agent.budget || {},
    sharedLessons: lessons(root),
    deadline: job.deadline || null, capabilities: agent.capabilities || [],
  };
  fs.writeFileSync(path.join(runDir, "brief.json"), JSON.stringify(brief, null, 2));
  ledger.add(runId, "spawn", { command: agent.command, lane: brief.lane });
  const child = spawn(agent.command[0], agent.command.slice(1), {
    cwd: agent.cwd || runDir, stdio: ["ignore", "pipe", "pipe"],
    env: { ...process.env, AGENT_RUN: runId, AGENT_NAME: agent.name },
  });
  const out = fs.createWriteStream(path.join(runDir, "output.log"));
  child.stdout.pipe(out); child.stderr.pipe(out);
  const handle = { agent, runId, runDir, ledger, child, stopped: null };
  handle.done = new Promise((resolve) => {
    child.on("exit", (code, signal) => {
      ledger.add(runId, "exit", { code, signal, stopped: handle.stopped });
      resolve({ code, signal });
    });
  });
  // Budget: wall-clock cap stops the run (spec S9).
  if (agent.budget.maxWallMs) {
    handle._budgetTimer = setTimeout(() => killAgent(handle, "budget-wall-clock"), agent.budget.maxWallMs);
    handle.done.then(() => clearTimeout(handle._budgetTimer));
  }
  // STOP file honoured at checkpoints (spec S6).
  handle._stopPoll = setInterval(() => {
    if (fs.existsSync(path.join(runDir, "STOP"))) killAgent(handle, "stop-file");
  }, 100);
  handle.done.then(() => clearInterval(handle._stopPoll));
  return handle;
}

export async function killAgent(handle, reason, graceMs = 800) {
  if (handle.stopped) return;
  handle.stopped = reason;
  handle.ledger.add(handle.runId, "stop-request", { reason });
  handle.child.kill("SIGTERM");
  const exited = await Promise.race([
    handle.done.then(() => true),
    new Promise((r) => setTimeout(() => r(false), graceMs)),
  ]);
  if (!exited) {
    handle.child.kill("SIGKILL");
    handle.ledger.add(handle.runId, "killed-hard", { reason });
    await handle.done;
  }
}

export function watchState(target) {
  if (target.type === "file") {
    try {
      const st = fs.statSync(target.path);
      return { exists: true, size: st.size, mtimeMs: Math.floor(st.mtimeMs) };
    } catch { return { exists: false }; }
  }
  throw new Error("watch: unsupported target type " + target.type);
}

export function pollWatch(targets, prev = {}) {
  const now = {}, changes = [];
  for (const t of targets) {
    const key = t.type + ":" + t.path;
    now[key] = watchState(t);
    if (prev[key] && JSON.stringify(prev[key]) !== JSON.stringify(now[key])) changes.push({ key, from: prev[key], to: now[key] });
  }
  return { state: now, changes };
}

/* ---- CLI ---- */
const HERE = path.dirname(url.fileURLToPath(import.meta.url));
if (process.argv[1] && path.resolve(process.argv[1]) === path.resolve(url.fileURLToPath(import.meta.url))) {
  const [, , cmd, name] = process.argv;
  const agents = loadRegistry(path.join(HERE, "registry.json"));
  if (cmd === "list") {
    for (const a of agents) console.log(a.name, "—", a.lane || "");
  } else if (cmd === "spawn" || cmd === "watch") {
    const agent = agents.find((a) => a.name === name);
    if (!agent) { console.error("no such agent: " + name); process.exit(1); }
    if (cmd === "spawn") {
      const h = spawnAgent(agent, { root: HERE });
      console.log("spawned", h.runId);
      await h.done;
    } else {
      const ledger = new Ledger(path.join(HERE, "watch.jsonl"));
      let prev = {};
      console.log("watching", (agent.watch || []).length, "targets for", name, "— Ctrl-C to stop");
      setInterval(() => {
        const { state, changes } = pollWatch(agent.watch || [], prev);
        prev = state;
        for (const c of changes) { ledger.add(name, "watch-change", c); console.log("CHANGE", c.key); }
      }, agent.watchCadenceMs || 2000);
    }
  } else {
    console.error("usage: runtime.mjs list | spawn <name> | watch <name>");
    process.exit(1);
  }
}
