// Meta OS agent layer — host runtime, slice 1 (docs/AGENT_LAYER_SPEC.md).
// Real spawn/kill, STOP file, budgets, watch poll/compare, and an
// append-only JSONL ledger per run. Zero dependencies.
//   node agents/runtime.mjs list            (registry entries)
//   node agents/runtime.mjs spawn <name>    (run one agent)
//   node agents/runtime.mjs watch <name>    (watch its targets)
import { spawn } from "node:child_process";
import { lessons } from "./lessons.mjs";
import { memoryDir, capFor, check, appendLedger } from "./memory.mjs";
import fs from "node:fs";
import path from "node:path";
import url from "node:url";

// B1 — every run leaves its full output on disk, timestamped and redacted.
// A secret must never land in a run log: any env value whose NAME looks like
// a key (KEY, TOKEN, SECRET, PASSWORD, PRIVATE, BEARER, SESSION, COOKIE,
// AUTH) is replaced, plus well-known token shapes (sk-…, ghp_…, xoxb-…,
// Bearer …). The replacement is by value, so even a child that echoes its own
// environment cannot leak the key into stdout.log. Nothing here truncates:
// the whole stream is written, because a teaser that hides the failure is a lie.
const SECRET_NAME_RE = /(key|token|secret|password|passwd|private|bearer|session|cookie|auth)/i;
const SECRET_SHAPES = [
  /sk-[A-Za-z0-9\-_]{8,}/g,
  /gh[pousr]_[A-Za-z0-9]{8,}/g,
  /xox[bpas]-[A-Za-z0-9\-]{8,}/g,
  /Bearer\s+[A-Za-z0-9\-._~+/=]{8,}/g,
];

export function redactSecrets(text) {
  let out = String(text == null ? "" : text);
  for (const [name, value] of Object.entries(process.env)) {
    if (typeof value !== "string" || value.length < 8) continue;
    if (!SECRET_NAME_RE.test(name)) continue;
    if (!out.includes(value)) continue;
    out = out.split(value).join("[REDACTED]");
  }
  for (const re of SECRET_SHAPES) {
    re.lastIndex = 0;
    out = out.replace(re, "[REDACTED]");
  }
  return out;
}

// One timestamped line per line: chunks are split on newlines and the partial
// tail is held until it completes or the run ends, so no line is stamped twice
// and none loses its time.
export function makeLineWriter(file) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  // The file exists from spawn, even when the stream stays silent: an absent
  // log must never read as a lost one.
  fs.appendFileSync(file, "");
  let tail = "";
  const append = (text) => fs.appendFileSync(file, text);
  const stampOf = (at) => (at instanceof Date ? at : new Date(at)).toISOString();
  return {
    write(chunk, at = new Date()) {
      const parts = (tail + String(chunk)).split("\n");
      tail = parts.pop();
      const stamp = stampOf(at);
      for (const line of parts) append(stamp + " " + redactSecrets(line) + "\n");
    },
    end(at = new Date()) {
      if (tail !== "") {
        append(stampOf(at) + " " + redactSecrets(tail) + "\n");
        tail = "";
      }
    },
  };
}

export function writeRunMeta(runDir, meta) {
  const file = path.join(runDir, "meta.json");
  fs.writeFileSync(file, JSON.stringify({ ...meta }, null, 2));
  return file;
}

export function loadRegistry(file) {
  const raw = JSON.parse(fs.readFileSync(file, "utf8"));
  if (!Array.isArray(raw.agents)) throw new Error("registry: 'agents' must be an array");
  const seen = new Set();
  for (const a of raw.agents) {
    if (!a.name || typeof a.name !== "string") throw new Error("registry: agent missing name");
    if (seen.has(a.name)) throw new Error("registry: duplicate agent " + a.name);
    seen.add(a.name);
    // A draft has no program yet, so it has no command. Anything else must
    // have one: an empty command on a live entry is a spawn that cannot work.
    if (!Array.isArray(a.command)) {
      if (a.draft === true) a.command = [];
      else throw new Error("registry: " + a.name + " missing command");
    }
    if (a.command.length === 0 && a.draft !== true) throw new Error("registry: " + a.name + " missing command");
    if (a.command.length > 0 && a.draft === true && a.command.join(" ") === "true") {
      throw new Error("registry: " + a.name + " still carries the placeholder command");
    }
    // Every argv element must be a string. `command: ["node", 42]` passes a length check and
    // then throws inside spawn() -- at spawn time, in a process that is already running the
    // rest of the crew. A malformed entry is refused at load, where nothing has started.
    for (const part of a.command) {
      if (typeof part !== "string") throw new Error("registry: " + a.name + " command must be strings");
    }
    a.budget = a.budget || {};
    if (a.budget.maxWallMs != null && !(a.budget.maxWallMs > 0)) throw new Error("registry: " + a.name + " bad maxWallMs");
    if (a.budget.maxCostUsd != null && !(a.budget.maxCostUsd >= 0)) throw new Error("registry: " + a.name + " bad maxCostUsd");
    // Watch targets are validated here for the same reason: `pollWatch` throws on an
    // unsupported target type, and today that throw happens inside a setInterval at the
    // watch cadence -- one typo in the registry kills the watcher minutes later, far from
    // the entry that caused it.
    if (a.watch != null) {
      if (!Array.isArray(a.watch)) throw new Error("registry: " + a.name + " watch must be an array");
      for (const t of a.watch) {
        if (!t || t.type !== "file" || typeof t.path !== "string" || t.path.length === 0) {
          throw new Error("registry: " + a.name + " bad watch target");
        }
      }
    }
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
    // A field called "run" or "event" lands after the record's own keys and
    // silently rewrites them: a memory failure was written as a second "exit"
    // line. Refuse the collision instead of writing a record that lies.
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
  // Read the events back.
  //
  // A crash can tear exactly one line: the last one, the append that was in flight when the
  // process died (a single appendFileSync is not a transaction). That line is skipped and
  // the rest of the history is returned, because a receipt with one truncated tail is still
  // the receipt of the run.
  //
  // A torn line anywhere ELSE is not a crash -- it is a rewritten or spliced file, which the
  // append-only rule forbids. That throws with its line number: an agent's history is the
  // evidence for everything else it claims, and quietly dropping the middle of it would make
  // every later line a claim about a run nobody can reconstruct.
  read() {
    if (!fs.existsSync(this.file)) return [];
    const lines = fs.readFileSync(this.file, "utf8").split("\n");
    const out = [];
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      if (!line) continue;
      try {
        out.push(JSON.parse(line));
      } catch (e) {
        const isLastContent = lines.slice(i + 1).every((l) => !l);
        if (isLastContent) return out;          // the tail a crash tore off
        throw new Error("ledger: torn line " + (i + 1) + " of " + this.file);
      }
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
  if (!Array.isArray(agent.command)) {
    if (agent.draft === true) agent.command = [];
    else throw new Error("registry: " + agent.name + " missing command");
  }
  if (agent.command.length === 0 && agent.draft !== true) {
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

// A full memory must not crash a run that is already exiting, and the refusal
// must not vanish either: the run ledger says the record was not written.
function noteMemory(memory, entry, ledger, runId) {
  if (!memory) return;
  try {
    appendLedger(memory.dir, entry, { maxBytes: memory.cap });
  } catch (error) {
    try {
      ledger.add(runId, "memory-write-failed", { record: entry.event, code: error.code || "error" });
    } catch { /* nothing left to write to */ }
  }
}

export function spawnAgent(agent, { root, job = {}, repoRoot } = {}) {
  const runId = agent.name + "-" + Date.now().toString(36);
  const runDir = path.join(root, "runs", runId);
  fs.mkdirSync(runDir, { recursive: true });
  const ledger = new Ledger(path.join(runDir, "ledger.jsonl"));
  // Two directories, two jobs. `root` is the relay state (runs, memory,
  // ledgers — writable, per user). `repoRoot` is the payload the commands
  // live in (read-only in the image). A `repo:` script path resolves against
  // the payload, never the state: resolving it against the state made every
  // staged command (agents/watchman.mjs included) a spawn-error ENOENT.
  // Callers that keep one tree (drills, tests) pass only `root` and the
  // payload defaults to it, so their behavior does not change.
  const codeBase = repoRoot || root;
  // The run clock starts here, before any gate, so even a refused run can say
  // when it was considered and how long the decision took.
  const startTime = new Date();
  const startEpochMs = Date.now();
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
    // A refused run never spawns, but it still leaves a loud record: the log
    // names the reason and the meta file carries the timing, so a budget
    // refusal never reads as a silent board.
    writeRunMeta(runDir, {
      run: runId, agent: agent.name, startTime: startTime.toISOString(),
      startEpochMs, endTime: new Date().toISOString(), endEpochMs: Date.now(),
      durationMs: Date.now() - startEpochMs,
      exitCode: null, signal: null, refused: gate.reason,
      estimateUsd: gate.estimate, capUsd: gate.cap,
    });
    const log = makeLineWriter(path.join(runDir, "stdout.log"));
    log.write("run refused before spawn: " + gate.reason +
      " (estimate " + gate.estimate + ", cap " + gate.cap + ")\n");
    log.end();
    makeLineWriter(path.join(runDir, "stderr.log")).end();
    return {
      agent, runId, runDir, ledger, child: null, stopped: gate.reason,
      done: Promise.resolve({ code: null, signal: null, refused: true }),
    };
  }

  // Spec §8: the cap is checked before anything starts, and a refusal looks
  // like the budget refusal, so a caller has one shape to handle.
  const memory = { dir: memoryDir(root, agent.name), cap: capFor(agent) };
  const refuseMemory = (usedBytes, capBytes) => {
    const receipt = {
      run: runId, reason: "memory-cap", usedBytes, capBytes,
      at: new Date().toISOString(),
    };
    ledger.add(runId, "memory-receipt", receipt);
    fs.writeFileSync(path.join(runDir, "receipt.json"), JSON.stringify(receipt, null, 2));
    ledger.add(runId, "refused", { reason: "memory-cap" });
    writeRunMeta(runDir, {
      run: runId, agent: agent.name, startTime: startTime.toISOString(),
      startEpochMs, endTime: new Date().toISOString(), endEpochMs: Date.now(),
      durationMs: Date.now() - startEpochMs,
      exitCode: null, signal: null, refused: "memory-cap",
      usedBytes, capBytes,
    });
    const log = makeLineWriter(path.join(runDir, "stdout.log"));
    log.write("run refused before spawn: memory-cap " +
      "(used " + usedBytes + " bytes, cap " + capBytes + " bytes)\n");
    log.end();
    makeLineWriter(path.join(runDir, "stderr.log")).end();
    return {
      agent, runId, runDir, ledger, child: null, stopped: "memory-cap", memory,
      done: Promise.resolve({ code: null, signal: null, refused: true }),
    };
  };
  const usedNow = check(memory.dir, memory.cap);
  if (!usedNow.ok) return refuseMemory(usedNow.bytes, memory.cap);
  try {
    appendLedger(memory.dir, {
      event: "spawn", run: runId, agent: agent.name, at: new Date().toISOString(),
    }, { maxBytes: memory.cap });
  } catch (error) {
    if (error.code !== "memory-cap") throw error;
    return refuseMemory(error.usage ?? usedNow.bytes, memory.cap);
  }

  const command = resolveCommand(agent.command, codeBase);
  ledger.add(runId, "spawn", { command, lane: brief.lane });
  // B1 — the run's own files. stdout.log and stderr.log carry one timestamped,
  // redacted line per line and are NEVER truncated; output.log stays as the
  // raw combined stream (redacted, not truncated) so anything reading the old
  // name keeps working; meta.json carries start/end time, duration and exit.
  writeRunMeta(runDir, {
    run: runId, agent: agent.name, startTime: startTime.toISOString(),
    startEpochMs, endTime: null, endEpochMs: null, durationMs: null,
    exitCode: null, signal: null, error: null,
  });
  const stdoutLog = makeLineWriter(path.join(runDir, "stdout.log"));
  const stderrLog = makeLineWriter(path.join(runDir, "stderr.log"));
  const child = spawn(command[0], command.slice(1), {
    cwd: agent.cwd || runDir, stdio: ["ignore", "pipe", "pipe"],
    env: { ...process.env, AGENT_RUN: runId, AGENT_NAME: agent.name },
  });
  const out = fs.createWriteStream(path.join(runDir, "output.log"));
  const feed = (writer) => (chunk) => {
    const text = chunk.toString("utf8");
    writer.write(text);
    out.write(redactSecrets(text));
  };
  if (child.stdout) child.stdout.on("data", feed(stdoutLog));
  if (child.stderr) child.stderr.on("data", feed(stderrLog));
  const handle = { agent, runId, runDir, ledger, child, stopped: null, exited: false, memory };
  handle.done = new Promise((resolve) => {
    child.on("exit", (code, signal) => {
      handle.exited = true;
      const endTime = new Date();
      const endEpochMs = Date.now();
      const durationMs = endEpochMs - startEpochMs;
      const failed = signal !== null || (code !== null && code !== 0);
      // B8 — a failure is loud in the log itself: a nonzero exit or a signal
      // gets a final line naming it, so a run that died quiet still says why.
      // The watchman result and the console row show the same line.
      if (failed) {
        stdoutLog.write("run failed: exit " + code + " signal " + signal +
          " after " + durationMs + "ms\n", endTime);
      } else {
        stdoutLog.write("run finished: exit 0 in " + durationMs + "ms\n", endTime);
      }
      stdoutLog.end(endTime); stderrLog.end(endTime);
      try { out.end(); } catch { /* the stream may already be gone */ }
      writeRunMeta(runDir, {
        run: runId, agent: agent.name, startTime: startTime.toISOString(),
        startEpochMs, endTime: endTime.toISOString(), endEpochMs, durationMs,
        exitCode: code, signal: signal || null, error: null,
      });
      ledger.add(runId, "exit", { code, signal, stopped: handle.stopped });
      noteMemory(memory, {
        event: "exit", run: runId, code, signal, stopped: handle.stopped,
        at: new Date().toISOString(),
      }, ledger, runId);
      resolve({ code, signal });
    });
    // A spawn that never becomes a process (ENOENT command, a cwd that does not exist, a
    // permission refusal) emits 'error' and NEVER emits 'exit'. With no listener that is an
    // uncaught exception that takes the runtime down -- and with the crew in the same
    // process, one bad registry entry would kill every other agent's parent. With a listener
    // that resolves nothing, `await handle.done` hangs forever. It does both jobs: the run is
    // marked failed in its own ledger and the promise settles.
    child.on("error", (err) => {
      handle.exited = true;    // never became a process: there is nothing left to stop
      const endTime = new Date();
      const endEpochMs = Date.now();
      const message = String(err && err.message || err);
      // A spawn that never starts must still leave the loud record: the log
      // names the missing binary or directory, the meta file carries it, and
      // the promise settles — no hang, no silence.
      stderrLog.write("spawn-error: " + message + "\n", endTime);
      stdoutLog.write("run failed to start: " + message + " (no process was created)\n", endTime);
      stdoutLog.end(endTime); stderrLog.end(endTime);
      try { out.end(); } catch { /* the stream may already be gone */ }
      writeRunMeta(runDir, {
        run: runId, agent: agent.name, startTime: startTime.toISOString(),
        startEpochMs, endTime: endTime.toISOString(), endEpochMs,
        durationMs: endEpochMs - startEpochMs,
        exitCode: null, signal: null, error: redactSecrets(message),
      });
      ledger.add(runId, "spawn-error", { message, stopped: handle.stopped });
      resolve({ code: null, signal: null, error: message });
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
  // A stop requested for a run that has already exited is not a stop. Writing the
  // receipt anyway makes the ledger say the runtime stopped something it never touched --
  // and the budget timer and the STOP poll both fire on their own schedule, so this is a
  // race a real run hits, not a synthetic one.
  if (handle.exited) return;
  handle.stopped = reason;
  handle.ledger.add(handle.runId, "stop-request", { reason });
  noteMemory(handle.memory, {
    event: "stop", run: handle.runId, reason, at: new Date().toISOString(),
  }, handle.ledger, handle.runId);
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

// Reconcile the run directories after a runtime restart (spec S12).
//
// A runtime that dies takes no children with it: the spawned agents keep running (or keep
// being dead) and their ledgers stop mid-story, with no `exit` line. Nothing on disk says so,
// so after a restart every one of those runs reads as "still going" to anything that scans the
// directory -- which is how a supervisor reports work that finished an hour ago.
//
// This walks `root/runs`, and for every run whose ledger has no terminal event it appends one:
// `{"event":"orphaned","reason":"runtime-died"}`. The ledger and the brief are preserved
// untouched -- the brief is what a baton hand-off reads, so a reconciliation that rewrote it
// would be the runtime editing the agent's orders. Idempotent: a run already marked is left
// alone, so a second restart does not stack marks.
// A refused run is terminal too: no child will ever write an exit line for
// it, and a recovery pass that marked it orphaned would claim work was lost
// that was never started. "refused" joins "exit" and "spawn-error" here.
const TERMINAL = new Set(["exit", "spawn-error", "refused"]);

export function reconcileRuns(root) {
  const runsDir = path.join(root, "runs");
  const marked = [], quiet = [], unreadable = [];
  if (!fs.existsSync(runsDir)) return { marked, quiet, unreadable };
  for (const name of fs.readdirSync(runsDir).sort()) {
    const runDir = path.join(runsDir, name);
    if (!fs.statSync(runDir).isDirectory()) continue;
    const ledgerFile = path.join(runDir, "ledger.jsonl");
    const ledger = new Ledger(ledgerFile);
    let events;
    try {
      events = ledger.read();
    } catch (e) {
      // A torn middle line is corruption, not a crash. It is reported, not repaired: the
      // only honest thing a recovery pass can say about a rewritten history is "I cannot
      // read this", and rewriting it would destroy the evidence either way.
      unreadable.push({ run: name, reason: String(e.message || e) });
      continue;
    }
    const last = events[events.length - 1];
    if (last && (TERMINAL.has(last.event) || last.event === "orphaned")) { quiet.push(name); continue; }
    ledger.add(name, "orphaned", { reason: "runtime-died", lastEvent: last ? last.event : null });
    marked.push(name);
  }
  return { marked, quiet, unreadable };
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
  } else if (cmd === "reconcile") {
    // Run this once after a runtime restart: it is the only thing that marks the runs a dead
    // runtime left without an exit line (spec S12).
    const res = reconcileRuns(HERE);
    console.log("reconcile: marked", res.marked.length, "quiet", res.quiet.length, "unreadable", res.unreadable.length);
    for (const r of res.marked) console.log("  orphaned", r);
    for (const r of res.unreadable) console.log("  UNREADABLE", r.run, "—", r.reason);
    if (res.unreadable.length > 0) process.exit(2);
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
    console.error("usage: runtime.mjs list | validate | spawn <name> | watch <name> | reconcile");
    process.exit(1);
  }
}
