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
    if (a.budget.maxCostUsd != null && !(a.budget.maxCostUsd >= 0)) throw new Error("registry: " + a.name + " bad maxCostUsd");
  }
  return raw.agents;
}

export class Ledger {
  constructor(file) { this.file = file; }
  add(run, event, fields = {}) {
    // CB-001: a record missing its identity is refused here, with the field
    // named, instead of being written and failing a reader later.
    for (const [name, value] of [["run", run], ["event", event]]) {
      if (typeof value !== "string" || value.trim() === "") {
        throw new Error("ledger: missing required field " + name);
      }
    }
    const line = JSON.stringify({ ts: new Date().toISOString(), run, event, ...fields }) + "\n";
    // A crash mid-append leaves a line with no trailing newline, and appending straight onto it
    // fuses the next record into the torn one -- so the record after the crash is lost as well.
    // One byte of separation is the whole fix; the reader skips the torn line it leaves behind.
    let sep = "";
    try {
      const st = fs.statSync(this.file);
      if (st.size > 0) {
        const fd = fs.openSync(this.file, "r");
        const b = Buffer.alloc(1);
        fs.readSync(fd, b, 0, 1, st.size - 1);
        fs.closeSync(fd);
        if (b[0] !== 0x0a) sep = "\n";
      }
    } catch { /* no file yet: nothing to separate from */ }
    fs.appendFileSync(this.file, sep + line);
    return line;
  }
  // A torn last line is what a crash mid-append leaves behind, and the old reader threw on it
  // and took every complete record before it down too: one bad append made the whole run's
  // history unreadable. Skipping is the smallest honest recovery -- it repairs nothing and
  // reorders nothing, it just keeps the records that are whole.
  read() {
    if (!fs.existsSync(this.file)) return [];
    const out = [];
    for (const line of fs.readFileSync(this.file, "utf8").split("\n")) {
      if (!line) continue;
      try { out.push(JSON.parse(line)); } catch { /* torn line: skip, keep the rest */ }
    }
    return out;
  }
}

// Registry commands must be portable: an absolute path to this checkout would make the file
// wrong on every other machine. `repo:node` means "this Node, plus a script inside the repo";
// the script argument is resolved against the repo root, never the run directory.
// CB-007: one validator for registry entries, usable by a CLI and by tests.
// Every entry must name itself, its lane, a non-empty argv, and a budget.
export function validateEntry(agent) {
  if (!agent || typeof agent !== "object") throw new Error("registry: entry must be an object");
  for (const field of ["name", "lane"]) {
    if (typeof agent[field] !== "string" || agent[field].trim() === "") {
      throw new Error("registry: missing field " + field + (agent.name ? " on " + agent.name : ""));
    }
  }
  if (!Array.isArray(agent.command) || agent.command.length === 0) {
    throw new Error("registry: " + agent.name + " missing command");
  }
  if (!agent.budget || typeof agent.budget !== "object") {
    throw new Error("registry: " + agent.name + " missing budget");
  }
  return true;
}

export function resolveCommand(command, root) {
  if (!Array.isArray(command) || command.length === 0) throw new Error("registry: missing command");
  const out = [...command];
  if (out[0] === "repo:node") {
    out[0] = process.execPath;
    if (out[1] && !path.isAbsolute(out[1])) out[1] = path.join(root, out[1]);
  }
  // Any later argument may opt into a repo-relative path (`repo:os-build/...`), which keeps a
  // registry entry portable without making every argument absolute.
  for (let i = 1; i < out.length; i++) {
    if (typeof out[i] === "string" && out[i].startsWith("repo:")) {
      out[i] = path.join(root, out[i].slice("repo:".length));
    }
  }
  return out;
}

// CB-378: a job's estimated cost is checked against the agent's own cap before
// anything is spawned. The check is one number against one cap on purpose -- a
// governor that guesses is worse than none -- and a missing estimate is NOT read
// as zero: it passes to the wall-clock budget and is recorded as unchecked.
export function preflightBudget(agent, job = {}) {
  const cap = agent && agent.budget ? agent.budget.maxCostUsd : undefined;
  const estimate = job ? job.estimatedCostUsd : undefined;
  if (cap == null) return { ok: true };
  if (typeof cap !== "number" || !(cap >= 0)) {
    throw new Error("registry: " + (agent && agent.name) + " bad maxCostUsd");
  }
  if (estimate == null) return { ok: true, unchecked: "no-estimate" };
  if (typeof estimate !== "number" || !Number.isFinite(estimate) || estimate < 0) {
    throw new Error("budget: estimatedCostUsd must be a non-negative number");
  }
  if (estimate > cap) {
    return { ok: false, reason: "budget-cost-cap", estimate, cap };
  }
  return { ok: true, estimate, cap };
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

  // CB-379: the refusal is recorded where the run's history lives -- the ledger
  // and the receipt both name the cap and the estimate -- and the returned handle
  // resolves like any other run, so a caller needs no special case for "never
  // started". No command is resolved and no process exists to kill.
  const gate = preflightBudget(agent, job);
  if (!gate.ok) {
    const receipt = {
      run: runId, reason: gate.reason, estimateUsd: gate.estimate,
      capUsd: gate.cap, at: new Date().toISOString(),
    };
    ledger.add(runId, "budget-receipt", receipt);
    fs.writeFileSync(path.join(runDir, "receipt.json"), JSON.stringify(receipt, null, 2));
    ledger.add(runId, "refused", { reason: gate.reason });
    return {
      agent, runId, runDir, ledger, child: null, stopped: gate.reason,
      done: Promise.resolve({ code: null, signal: null, refused: true }),
    };
  }

  const command = resolveCommand(agent.command, root);
  ledger.add(runId, "spawn", { command, lane: brief.lane });
  const child = spawn(command[0], command.slice(1), {
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
    handle._budgetTimer = setTimeout(() => {
      // The receipt is written BEFORE the kill, so a crash during the kill cannot leave a run
      // that was stopped by its budget with no record of why (R11-259).
      const receipt = {
        run: runId, reason: "budget-wall-clock", capMs: agent.budget.maxWallMs,
        at: new Date().toISOString(),
      };
      ledger.add(runId, "budget-receipt", receipt);
      try { fs.writeFileSync(path.join(runDir, "receipt.json"), JSON.stringify(receipt, null, 2)); } catch { /* ledger still has it */ }
      killAgent(handle, "budget-wall-clock");
    }, agent.budget.maxWallMs);
    handle.done.then(() => clearTimeout(handle._budgetTimer));
  }
  // STOP file honoured at checkpoints (spec S6). The default stays 100 ms; a drill may ask for
  // a tighter poll, and that choice is visible in the agent object rather than hidden in a test.
  const stopPollMs = Number(agent.stopPollMs) > 0 ? Number(agent.stopPollMs) : 100;
  handle._stopPoll = setInterval(() => {
    if (fs.existsSync(path.join(runDir, "STOP"))) killAgent(handle, "stop-file");
  }, stopPollMs);
  handle.done.then(() => clearInterval(handle._stopPoll));
  return handle;
}

export async function killAgent(handle, reason, graceMs = 800) {
  if (handle.stopped) return;
  // A refused run has no child; it is already stopped and its receipt says why.
  if (!handle.child) return;
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

// A change is a quiet note unless it moved at least this many bytes. A file
// that appears or disappears is never quiet: a create or a delete is the whole
// change, whatever its size. The threshold is here, not in a caller, so every
// watcher sizes a change the same way.
export const LARGE_CHANGE_BYTES = 4096;

function classifyChange(from, to, threshold = LARGE_CHANGE_BYTES) {
  if (!from.exists || !to.exists) return { kind: "alarm", deltaBytes: null, reason: from.exists ? "deleted" : "created" };
  const deltaBytes = Math.abs(to.size - from.size);
  return { kind: deltaBytes >= threshold ? "alarm" : "note", deltaBytes, reason: null };
}

export function pollWatch(targets, prev = {}) {
  const now = {}, changes = [];
  for (const t of targets) {
    const key = t.type + ":" + t.path;
    now[key] = watchState(t);
    if (prev[key] && JSON.stringify(prev[key]) !== JSON.stringify(now[key])) {
      changes.push({ key, from: prev[key], to: now[key], ...classifyChange(prev[key], now[key]) });
    }
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
  } else if (cmd === "validate") {
    for (const a of agents) validateEntry(a);
    console.log("registry ok: " + agents.length + " entries");
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
    console.error("usage: runtime.mjs list | validate | spawn <name> | watch <name>");
    process.exit(1);
  }
}
