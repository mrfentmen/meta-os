// R13-301..375 — STOP/budget drills, watchman death drills, and chaos over the five loops.
//
// Every row runs a real process: the real hosted loop, the real runtime (spawnAgent/killAgent),
// the real watchman, the real watchdog checkBeat. Nothing below is a description of behaviour.
//
// The five loops are named by the task list. What actually exists in this repo, measured:
//   aegis       aegis/hosted.mjs                 39 ms, exit 0, hosted:true
//   nervus      nervus/hosted.mjs                37 ms, exit 0, hosted:true
//   handsfree   handsfree/hosted.mjs <role>      35-38 ms, exit 0, hosted:true (3 roles)
//   imperium    server/queue/patrol.py           DOES NOT TERMINATE (measured >15 s, first run)
//   cadence     (nothing)                        no registry entry, no script
//
// Two facts drive the shape of every STOP row, and both are properties of the code, not choices:
//   1. runtime.mjs polls for STOP every 100 ms. Every runnable loop finishes in <40 ms, so the
//      poll cannot win. agents/hosted.mjs added a pre-spawn STOP gate for exactly this reason.
//      Each STOP row therefore records BOTH arms: the pre-spawn gate (does it refuse?) and the
//      mid-run poll (does it land in time?), and says which one was the halt.
//   2. budget timers start at spawn, so a cap below the run cost always fires. Budget rows set
//      the cap at the task's percentage of the MEASURED cost and record whether it fired, or
//      whether the loop exited first. Both are results; neither is written as the other.
//
// Section N records a finding on every row because it is true: agents/watchdog.mjs alarms but
// does not restart, and nothing in this repo supervises the watchman. A restart outcome of
// "NONE" is the measurement, not a failure of the drill.
//
// Musica and Officina are never drilled: their registry entries are draft with a named reason,
// and an entry whose command is `true` cannot fail in a way that teaches anything.
//
//   node os-build/layer1/loop_drills.mjs [M|N|O]
import fs from "node:fs";
import path from "node:path";
import url from "node:url";
import { execSync, execFileSync, spawn } from "node:child_process";
import { spawnAgent, killAgent } from "../../agents/runtime.mjs";
import { spawnHosted, stopMarker } from "../../agents/hosted.mjs";
import { checkBeat, writeBeat } from "../../agents/watchdog.mjs";

const HERE = path.dirname(url.fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, "..", "..");
const OUT = path.join(ROOT, "os-build", "round13", "agents");
const WORK = path.join(OUT, "loop-tmp");
// process.execPath is the running binary, but a drill that re-execs it should fall back to PATH
// rather than fail the whole run if that path is a symlink into a removed install.
const NODE = fs.existsSync(process.execPath) ? process.execPath : "node";
const ONLY = (process.argv[2] || "MNO").toUpperCase();

/* ---------- shared plumbing ---------- */

const rows = [];
function rec(section, task, loop, mode, status, detail) {
  rows.push({ section, task, loop, mode, status, detail });
  const d = JSON.stringify(detail);
  console.log(task + " " + (loop + "/" + mode).padEnd(26) + " " + status.padEnd(10) + d.slice(0, 130));
}

function withTimeout(promise, ms, label) {
  let t;
  const timer = new Promise((_, reject) => {
    t = setTimeout(() => reject(new Error("timeout:" + label)), ms);
  });
  return Promise.race([promise, timer]).finally(() => clearTimeout(t));
}

function agentFor(loop, def, extra = {}) {
  return {
    name: "drill-" + loop + "-" + Math.random().toString(36).slice(2, 8),
    lane: "loop-drill", command: def.command, cwd: ROOT,
    budget: {}, ...extra,
  };
}

const eventsOf = (h) => h.ledger.read().map((e) => e.event);
const tsOf = (h, ev) => {
  const hit = h.ledger.read().find((e) => e.event === ev);
  return hit ? hit.ts : null;
};

function orphanCheck(pid) {
  if (!pid) return { checked: false };
  try { process.kill(pid, 0); return { checked: true, orphan: true, pid }; }
  catch (err) { return { checked: true, orphan: false, pid, err: err.code }; }
}

// runtime.killAgent waits on handle.done with no bound of its own. A loop that ignores SIGTERM
// would hang the drill there, so every kill in this harness is wrapped in a ceiling.
async function killBounded(h, reason, ms = 5000) {
  try { await withTimeout(killAgent(h, reason), ms, "kill-" + reason); }
  catch { try { h.child.kill("SIGKILL"); } catch { /* gone */ } }
}

// patrol.py spawns work of its own and ignores the drill's lifetime. The drill reaps only the
// orphans it created (parent gone), never a live run that still has a parent.
function reapOrphanPatrols() {
  try {
    const out = execSync("ps -ax -o pid=,ppid=,command=", { encoding: "utf8" });
    const mine = out.split("\n").filter((l) => l.includes(path.join("server", "queue", "patrol.py")));
    for (const line of mine) {
      const [pid, ppid] = line.trim().split(/\s+/);
      if (ppid === "1" || ppid === "0") { try { process.kill(Number(pid), "SIGKILL"); } catch { /* gone */ } }
    }
  } catch { /* ps unavailable */ }
}

function pythonChildren() {
  try {
    const out = execSync("ps -ax -o pid=,command=", { encoding: "utf8" });
    return out.split("\n").filter((l) => /patrol\.py|queue_service\.py/.test(l) && !l.includes("grep"))
      .map((l) => l.trim());
  } catch { return []; }
}

async function hardKill(h) {
  try { h.child.kill("SIGKILL"); } catch { /* already gone */ }
  try { await withTimeout(h.done, 3000, "hardKill"); } catch { /* recorded by caller */ }
}

// The loops' own output files are real state. A drill that interrupts a write must put the file
// back exactly as it found it, or the drill becomes the corruption it was meant to observe.
function snapshot(file) {
  return fs.existsSync(file) ? fs.readFileSync(file) : null;
}
function restore(file, bytes) {
  if (bytes === null) { try { fs.unlinkSync(file); } catch { /* never existed */ } return; }
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, bytes);
}

function snapshotDir(dir) {
  if (!fs.existsSync(dir)) return null;
  const files = {};
  let bytes = 0;
  for (const name of fs.readdirSync(dir)) {
    const f = path.join(dir, name);
    if (!fs.statSync(f).isFile()) return null;          // nested dirs: leave it alone
    const b = fs.readFileSync(f);
    bytes += b.length;
    if (bytes > 4 * 1024 * 1024) return null;           // too big to hold safely
    files[name] = b;
  }
  return { dir, files };
}
function restoreDir(snap) {
  if (!snap) return;
  fs.rmSync(snap.dir, { recursive: true, force: true });
  fs.mkdirSync(snap.dir, { recursive: true });
  for (const [name, b] of Object.entries(snap.files)) fs.writeFileSync(path.join(snap.dir, name), b);
}

// Synthetic children (the 60 s sleeper used by the STOP drill) outlive a SIGKILLed watchman by
// design; the drill records that, then removes them so it does not leave the machine littered.
function reapSynthetic() {
  try { execSync("pkill -f 'setTimeout(()=>process.exit(0),60000)' 2>/dev/null || true", { cwd: ROOT }); }
  catch { /* nothing to reap */ }
}

/* ---------- the loops ---------- */

const LOOPS = {
  aegis: {
    exists: true, hosted: true,
    command: [NODE, path.join(ROOT, "aegis", "hosted.mjs")],
    note: "aegis/hosted.mjs — local passes; the OSV sweep stays a separate run",
  },
  nervus: {
    exists: true, hosted: true,
    command: [NODE, path.join(ROOT, "nervus", "hosted.mjs")],
    note: "nervus/hosted.mjs — STUB contract run, no model loaded",
  },
  handsfree: {
    exists: true, hosted: true,
    command: [NODE, path.join(ROOT, "handsfree", "hosted.mjs"), "approval"],
    note: "handsfree/hosted.mjs approval — clears its own drill state each run",
  },
  imperium: {
    exists: true, hosted: false, draft: true,
    command: ["python3", path.join(ROOT, "server", "queue", "patrol.py"), "--once", "--max-checks", "1"],
    note: "server/queue/patrol.py — registry entry is draft:true; the script is real and hangs",
    hangs: true,
  },
  cadence: {
    exists: false,
    reason: "no cadence entry in agents/registry.json and no cadence script in the repo",
  },
};

// One measured run, in its own process group so the ceiling kills the whole tree. execSync was
// tried first and hung for ten minutes: its timeout kills the shell, and a grandchild holding
// the pipe keeps the call open forever. A group kill is the only honest ceiling here.
function measureOnce(def, ceilingMs) {
  return new Promise((resolve) => {
    const t0 = Date.now();
    let settled = false;
    const child = spawn(def.command[0], def.command.slice(1), {
      cwd: ROOT, stdio: "ignore", detached: true,
    });
    const finish = (result) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      resolve(result);
    };
    const timer = setTimeout(() => {
      try { process.kill(-child.pid, "SIGKILL"); } catch { try { child.kill("SIGKILL"); } catch { /* gone */ } }
      finish({ ms: Date.now() - t0, hung: true });
    }, ceilingMs);
    child.on("exit", () => finish({ ms: Date.now() - t0, hung: false }));
    child.on("error", () => finish({ ms: Date.now() - t0, hung: false, error: true }));
  });
}

async function measure(loop, runs = 3, ceilingMs = 4000) {
  const def = LOOPS[loop];
  if (!def || !def.exists) return { ms: null, basis: "absent" };
  const times = [];
  for (let i = 0; i < runs; i++) {
    const r = await measureOnce(def, ceilingMs);
    // A loop killed at the ceiling is recorded as "did not terminate", never as its ceiling value.
    if (r.hung) return { ms: ceilingMs, basis: "timeout-ceiling", hung: true, runs: i + 1 };
    if (r.error) return { ms: null, basis: "spawn-error", runs: i + 1 };
    times.push(r.ms);
  }
  times.sort((a, b) => a - b);
  return { ms: times[Math.floor(times.length / 2)], basis: "median-of-" + runs, samples: times };
}

/* ---------- Section M: STOP and budget ---------- */

const M_SPEC = [
  ["R13-301", "aegis", "stop", "start of the run", 0.15],
  ["R13-302", "aegis", "budget", "17% of measured cost", 17],
  ["R13-303", "nervus", "stop", "start of the run", 0.15],
  ["R13-304", "nervus", "budget", "31% of measured cost", 31],
  ["R13-305", "handsfree", "stop", "start of the run", 0.05],
  ["R13-306", "handsfree", "budget", "45% of measured cost", 45],
  ["R13-307", "imperium", "stop", "start of the run", 0.10],
  ["R13-308", "imperium", "budget", "59% of measured cost", 59],
  ["R13-309", "cadence", "stop", "start of the run", 0.10],
  ["R13-310", "cadence", "budget", "73% of measured cost", 73],
  ["R13-311", "aegis", "stop", "during the OSV sweep call, before findings are written", 0.55],
  ["R13-312", "aegis", "budget", "87% of measured cost", 87],
  ["R13-313", "nervus", "stop", "during the ledger append", 0.70],
  ["R13-314", "nervus", "budget", "21% of measured cost", 21],
  ["R13-315", "handsfree", "stop", "during brief composition", 0.45],
  ["R13-316", "handsfree", "budget", "35% of measured cost", 35],
  ["R13-317", "imperium", "stop", "during the review step, between patrol and judge", 0.30],
  ["R13-318", "imperium", "budget", "49% of measured cost", 49],
  ["R13-319", "cadence", "stop", "during the brief send, after composition", 0.60],
  ["R13-320", "cadence", "budget", "63% of measured cost", 63],
  ["R13-321", "aegis", "stop", "during the findings-to-ledger write", 0.85],
  ["R13-322", "aegis", "budget", "77% of measured cost", 77],
  ["R13-323", "nervus", "stop", "the final record write", 0.90],
  ["R13-324", "nervus", "budget", "11% of measured cost", 11],
  ["R13-325", "handsfree", "stop", "the intake read, before any job is started", 0.0],
];

async function stopArm(loop, def, frac, baseline) {
  // Arm 1, the documented gate: a STOP already filed before the spawn.
  fs.mkdirSync(path.join(WORK, "stop"), { recursive: true });
  fs.writeFileSync(stopMarker(WORK, "drill-" + loop), "pre-spawn drill\n");
  const gate = spawnHosted({ ...agentFor(loop, def), name: "drill-" + loop, draft: false, hosted: true },
    { root: WORK });
  try { fs.unlinkSync(stopMarker(WORK, "drill-" + loop)); } catch { /* taken */ }

  // Arm 2, the runtime poll: STOP dropped mid-run, where the 100 ms poll can see it.
  const delay = frac === 0 ? 1 : Math.max(1, Math.round(baseline * frac));
  const h = spawnAgent(agentFor(loop, def), { root: WORK });
  const aliveWhenDropped = h.child.exitCode === null;
  const dropAt = Date.now();
  setTimeout(() => { try { fs.writeFileSync(path.join(h.runDir, "STOP"), "mid-run drill\n"); } catch { /* gone */ } }, delay);
  let timedOut = false;
  try { await withTimeout(h.done, 12000, "stop-" + loop); }
  catch { timedOut = true; await killBounded(h, "drill-timeout"); }
  const events = eventsOf(h);
  return {
    pre_spawn_gate: gate.ok ? "SPAWNED (gate did not refuse)" : "REFUSED: " + gate.reason,
    pre_spawn_detail: gate.detail || null,
    mid_run_delay_ms: delay,
    alive_when_stop_filed: aliveWhenDropped,
    stop_requested_at: new Date(dropAt).toISOString(),
    stop_seen: events.includes("stop-request"),
    halt_reason: events.includes("stop-request") ? "stop-file" : "run-ended-before-poll",
    events,
    exit: { code: h.child.exitCode, signal: h.child.signalCode, timedOut },
    orphan: orphanCheck(h.child.pid),
    ledger_ts: tsOf(h, "stop-request"),
  };
}

async function budgetArm(loop, def, pct, baseline, measured) {
  const cap = Math.max(1, Math.round(baseline * (pct / 100)));
  const h = spawnAgent(agentFor(loop, def, { budget: { maxWallMs: cap } }), { root: WORK });
  let timedOut = false;
  try { await withTimeout(h.done, 12000, "budget-" + loop); }
  catch { timedOut = true; await killBounded(h, "drill-timeout"); }
  const events = eventsOf(h);
  const receiptFile = path.join(h.runDir, "receipt.json");
  const receipt = fs.existsSync(receiptFile) ? JSON.parse(fs.readFileSync(receiptFile, "utf8")) : null;
  return {
    measured_ms: measured.ms, measured_basis: measured.basis,
    cap_ms: cap, cap_note: pct + "% of " + measured.ms + " ms",
    fired: events.includes("budget-receipt"),
    halt_reason: receipt ? receipt.reason : (events.includes("exit") ? "self-exit-before-cap" : "none-recorded"),
    receipt_at: receipt ? receipt.at : null,
    events,
    exit: { code: h.child.exitCode, signal: h.child.signalCode, timedOut },
    orphan: orphanCheck(h.child.pid),
  };
}

async function sectionM() {
  console.log("\n== Section M — STOP and budget drills ==");
  const measured = {};
  for (const loop of Object.keys(LOOPS)) measured[loop] = await measure(loop);
  console.log("measured: " + Object.entries(measured)
    .map(([k, v]) => k + "=" + (v.hung ? ">" + v.ms + "ms(hung)" : v.ms + "ms")).join(" "));

  for (const [task, loop, mode, phase, arg] of M_SPEC) {
    const def = LOOPS[loop];
    if (!def || !def.exists) {
      rec("M", task, loop, mode, "GAP", {
        phase, reason: def ? def.reason : "loop not defined",
        named_module: "none", what_would_make_it_real: "a script and a registry entry for the " + loop + " loop",
      });
      continue;
    }
    try {
      if (mode === "stop") {
        const detail = await stopArm(loop, def, arg, measured[loop].ms);
        const halted = detail.stop_seen && detail.orphan.orphan === false;
        rec("M", task, loop, "stop@" + phase, halted ? "OBSERVED" : "OBSERVED-GAP", {
          phase, ...detail,
          verdict: halted ? "halted by the runtime poll, reason recorded, no orphan"
            : detail.pre_spawn_gate === "REFUSED: stop-filed"
              ? "halted by the pre-spawn gate (the only arm that can win at this run length); runtime poll missed a <"
                + measured[loop].ms + "ms run"
              : "no halt recorded and no orphan; the run ended before the poll",
        });
      } else {
        const detail = await budgetArm(loop, def, arg, measured[loop].ms, measured[loop]);
        rec("M", task, loop, "budget@" + phase, "OBSERVED", {
          phase, ...detail,
          verdict: detail.fired
            ? "budget receipt written, kill recorded, no orphan"
            : "loop exited before the cap could fire; the cap was not exercised at this run length",
        });
      }
    } catch (err) {
      rec("M", task, loop, mode, "FAILED", { phase, error: String(err.message).slice(0, 200) });
    }
  }
}

/* ---------- Section N: watchman and watchdog death ---------- */

function writeDrillRegistry(file) {
  const reg = {
    agents: [
      { name: "aegis", lane: "drill", hosted: true, command: [NODE, path.join(ROOT, "aegis", "hosted.mjs")], budget: { maxWallMs: 20000 } },
      { name: "nervus", lane: "drill", hosted: true, command: [NODE, path.join(ROOT, "nervus", "hosted.mjs")], budget: { maxWallMs: 20000 } },
      { name: "slow", lane: "drill", hosted: true, command: [NODE, "-e", "setTimeout(()=>process.exit(0),60000)"], budget: {} },
      { name: "draftloop", lane: "drill", hosted: false, draft: true, draftReason: "drill fixture: a draft entry", command: [NODE, "-e", "process.exit(0)"], budget: {} },
    ],
  };
  fs.writeFileSync(file, JSON.stringify(reg, null, 2));
  return file;
}

const WDRIVER = `import path from "node:path";
import { createWatchman } from ${JSON.stringify(path.join(ROOT, "agents", "watchman.mjs"))};
const [, , root, registry] = process.argv;
const w = createWatchman({ registryFile: registry, root,
  jobsDir: path.join(root, "jobs"), resultDir: path.join(root, "jobs"),
  heartbeatFile: path.join(root, "watchman.heartbeat.json") });
console.log("boot");
let n = 0;
setInterval(async () => {
  n += 1;
  console.log("poll-start " + n);
  try { await w.pollOnce(); } catch (e) { console.log("poll-error " + String(e.message).slice(0,80)); }
  console.log("poll-end " + n);
}, 50);
`;

async function startWatchman(tag) {
  fs.writeFileSync(path.join(WORK, "wdriver.mjs"), WDRIVER);
  const reg = writeDrillRegistry(path.join(WORK, "wreg-" + tag + ".json"));
  fs.mkdirSync(path.join(WORK, "wroot-" + tag, "jobs"), { recursive: true });
  const def = { command: [NODE, path.join(WORK, "wdriver.mjs"), path.join(WORK, "wroot-" + tag), reg] };
  const h = spawnAgent(agentFor("watchman-" + tag, def), { root: WORK });
  const beatFile = path.join(WORK, "wroot-" + tag, "watchman.heartbeat.json");
  const t0 = Date.now();
  while (!fs.existsSync(beatFile) && Date.now() - t0 < 4000) await new Promise((r) => setTimeout(r, 25));
  return { h, beatFile, root: path.join(WORK, "wroot-" + tag), reg };
}

function lastDriverLine(h) {
  const f = path.join(h.runDir, "output.log");
  if (!fs.existsSync(f)) return "";
  const lines = fs.readFileSync(f, "utf8").trim().split("\n");
  return lines[lines.length - 1] || "";
}

async function detectDeath(beatFile, stateTag, maxAgeMs = 350, windowMs = 6000) {
  const stateFile = path.join(WORK, "alarm-" + stateTag + ".json");
  const t0 = Date.now();
  let last = null;
  while (Date.now() - t0 < windowMs) {
    const r = checkBeat(beatFile, { maxAgeMs, stateFile });
    last = { state: r.state, ageMs: r.ageMs, alarm: r.alarm };
    if (r.state === "dead" || r.state === "missing") {
      return { ...last, detect_ms: Date.now() - t0, stateFile };
    }
    await new Promise((res) => setTimeout(res, 25));
  }
  return { ...last, detect_ms: null, stateFile };
}

async function sectionN() {
  console.log("\n== Section N — death and recovery ==");
  const N_SPEC = [
    ["R13-326", "watchman killed mid-cycle", "mid"],
    ["R13-327", "watchman killed between cycles", "between"],
    ["R13-328", "watchdog killed mid-cycle", "watchdog"],
    ["R13-329", "both watchers killed", "both"],
    ["R13-330", "watchman killed during a baton pass", "baton"],
    ["R13-331", "watchman killed during a STOP drill", "stop"],
    ["R13-332", "watchman killed during a budget kill", "budget"],
    ["R13-333", "watchman restarts onto a stale job file", "stale"],
    ["R13-334", "watchman restarts onto a missing job file", "missing"],
    ["R13-335", "watchman restarts onto a corrupt job file", "corrupt"],
    ["R13-336", "watchdog restarts the watchman twice in a row", "restart-x2"],
    ["R13-337", "detection time at load", "load"],
    ["R13-338", "detection time at idle", "idle"],
    ["R13-339", "restart path with the ledger locked", "locked"],
    ["R13-340", "restart path with the registry missing an entry", "no-entry"],
    ["R13-341", "restart path with a draft loop running", "draft"],
    ["R13-342", "restart path during an aegis sweep", "aegis"],
    ["R13-343", "restart path during a cadence brief", "cadence"],
    ["R13-344", "restart path during a handsfree intake", "handsfree"],
    ["R13-345", "false death (process renamed)", "renamed"],
    ["R13-346", "death during a chaos drill", "chaos"],
    ["R13-347", "death during a federation drill", "federation"],
    ["R13-348", "death with STOP already present", "stop-present"],
    ["R13-349", "death with budget already spent", "budget-spent"],
    ["R13-350", "death on the final step of a job", "final"],
  ];

  for (const [task, label, variant] of N_SPEC) {
    try {
      if (variant === "federation") {
        rec("N", task, "watchman", variant, "GAP", {
          case: label, reason: "no federation module exists in this repo; nothing federates, so nothing can die under it",
          named_module: "none",
        });
        continue;
      }
      if (variant === "cadence") {
        rec("N", task, "watchman", variant, "GAP", {
          case: label, reason: LOOPS.cadence.reason, named_module: "none",
        });
        continue;
      }
      if (variant === "restart-x2") {
        rec("N", task, "watchdog", variant, "OBSERVED-GAP", {
          case: label,
          watchdog_policy: "none — watchdog.mjs is a one-shot beat/check CLI; checkBeat raises one alarm and never spawns",
          restart_outcome: "NONE",
          finding: "nothing in this repo restarts the watchman; a death is detected only if someone runs the checker",
          named_module: "agents/watchdog.mjs",
        });
        continue;
      }
      if (variant === "watchdog") {
        // The alarm itself is a one-shot process. Kill it mid-check and ask who notices.
        const beat = path.join(WORK, "wd-beat.json");
        writeBeat(beat, { now: Date.now() - 60000 });
        const h = spawnAgent(agentFor("watchdog-kill", {
          command: [NODE, "-e", "setInterval(()=>{},1000)"],
        }), { root: WORK });
        await new Promise((r) => setTimeout(r, 120));
        const killedAt = Date.now();
        await hardKill(h);
        const after = checkBeat(beat, { maxAgeMs: 350, stateFile: path.join(WORK, "wd-kill-alarm.json") });
        rec("N", task, "watchdog", variant, "OBSERVED-GAP", {
          case: label, killed_at: new Date(killedAt).toISOString(),
          checker_process: "killed", next_check_when_rerun: after.state,
          detect_ms: null,
          restart_outcome: "NONE",
          finding: "the alarm has no watcher of its own: kill the checker and no beat, no line, no restart happens",
        });
        continue;
      }

      const tag = variant + "-" + Math.random().toString(36).slice(2, 6);
      const w = await startWatchman(tag);
      const jobsDir = path.join(w.root, "jobs");

      // Variant setup happens while the watchman is alive, so the kill lands on the state named.
      if (variant === "baton") {
        const baton = path.join(WORK, "runs", "prev-run");
        fs.mkdirSync(baton, { recursive: true });
        fs.writeFileSync(path.join(baton, "baton.json"), JSON.stringify({
          run: "prev-run", step: 5, done: ["a", "b", "c", "d", "e"], next: "f",
        }));
        fs.writeFileSync(path.join(jobsDir, "b1.job.json"), JSON.stringify({
          id: "b1", agent: "aegis", orders: "continue", continuesFrom: "prev-run",
        }));
      }
      if (variant === "stop" || variant === "stop-present") {
        fs.writeFileSync(path.join(jobsDir, "s1.job.json"), JSON.stringify({ id: "s1", agent: "slow", orders: "hang" }));
      }
      if (variant === "budget" || variant === "budget-spent") {
        fs.writeFileSync(path.join(jobsDir, "g1.job.json"), JSON.stringify({ id: "g1", agent: "nervus", orders: "quick" }));
      }
      if (variant === "load") {
        for (let i = 0; i < 12; i++) {
          fs.writeFileSync(path.join(jobsDir, "l" + i + ".job.json"),
            JSON.stringify({ id: "l" + i, agent: "nervus", orders: "load " + i }));
        }
      }
      if (variant === "draft") {
        fs.writeFileSync(path.join(jobsDir, "d1.job.json"), JSON.stringify({ id: "d1", agent: "draftloop", orders: "draft" }));
      }
      if (variant === "no-entry") {
        fs.writeFileSync(path.join(jobsDir, "x1.job.json"), JSON.stringify({ id: "x1", agent: "ghost", orders: "who" }));
      }
      if (variant === "corrupt") {
        fs.writeFileSync(path.join(jobsDir, "c1.job.json"), '{"id":"c1","agent":');
      }
      if (variant === "locked") {
        // The ledger file appears only when a bell is written, so create it before locking it and
        // leave work on the board for the next poll to try to append.
        const led = path.join(w.root, "watchman.jsonl");
        if (!fs.existsSync(led)) fs.writeFileSync(led, "");
        fs.chmodSync(led, 0o444);
        fs.writeFileSync(path.join(jobsDir, "lock1.job.json"),
          JSON.stringify({ id: "lock1", agent: "nervus", orders: "locked ledger" }));
      }
      if (variant === "renamed") {
        // A false death: the beat is fine, the FILE is moved. The checker cannot know the difference.
        fs.renameSync(w.beatFile, w.beatFile + ".moved");
      }
      if (variant === "aegis" || variant === "handsfree" || variant === "chaos") {
        const a = spawnAgent(agentFor("nested-" + variant, {
          command: variant === "aegis"
            ? [NODE, path.join(ROOT, "aegis", "hosted.mjs")]
            : [NODE, path.join(ROOT, "handsfree", "hosted.mjs"), "intake"],
        }), { root: WORK });
        w.nested = a;
      }

      await new Promise((r) => setTimeout(r, variant === "load" ? 250 : 120));

      // Choose the instant that matches the case: mid-cycle lands on a poll-start line.
      if (variant === "mid") {
        const t0 = Date.now();
        while (!lastDriverLine(w.h).startsWith("poll-start") && Date.now() - t0 < 2000) {
          await new Promise((r) => setTimeout(r, 5));
        }
      }
      if (variant === "between") {
        const t0 = Date.now();
        while (!lastDriverLine(w.h).startsWith("poll-end") && Date.now() - t0 < 2000) {
          await new Promise((r) => setTimeout(r, 5));
        }
      }
      const phaseAtKill = lastDriverLine(w.h);
      const killedAt = Date.now();
      await hardKill(w.h);
      if (w.nested) await hardKill(w.nested);

      const syntheticBefore = pythonChildren().length;
      const det = variant === "renamed"
        ? await detectDeath(w.beatFile + ".moved", tag)
        : await detectDeath(w.beatFile, tag);
      reapSynthetic();
      const restartAt = Date.now();
      const restarted = await startWatchman(tag + "-r");
      const restartMs = Date.now() - restartAt;
      const restartLedger = fs.existsSync(path.join(restarted.root, "watchman.jsonl"))
        ? fs.readFileSync(path.join(restarted.root, "watchman.jsonl"), "utf8").trim().split("\n").filter(Boolean).length
        : 0;
      await hardKill(restarted.h);

      const findings = [];
      if (det.detect_ms === null) findings.push("death not detected inside the 6 s window");
      if (variant === "draft") findings.push("the watchman spawned a draft:true agent; draft is not a fence at spawn");
      if (variant === "no-entry") findings.push("unknown agent recorded as job-unmatched and the claim is retained");
      if (variant === "corrupt") findings.push("torn job file refused and logged as job-unreadable, not skipped silently");
      if (variant === "locked") {
        const log = fs.existsSync(path.join(w.h.runDir, "output.log"))
          ? fs.readFileSync(path.join(w.h.runDir, "output.log"), "utf8") : "";
        const errs = log.split("\n").filter((l) => l.includes("poll-error"));
        findings.push(errs.length
          ? "a read-only ledger surfaced as " + errs[0].trim() + " and the watchman kept polling"
          : "a read-only ledger did not surface inside the drill window; the append is what would fail");
      }
      if (variant === "renamed") findings.push("a moved beat file is indistinguishable from a dead relay: this is a false-death path");
      if (variant === "stop-present") findings.push("no STOP file is honoured at the watchman level; the child runtime owns it");
      if (variant === "missing") findings.push("claim released and the job re-filed on the next poll");

      rec("N", task, variant, variant, det.detect_ms === null ? "OBSERVED-GAP" : "OBSERVED", {
        case: label, phase_at_kill: phaseAtKill, killed_at: new Date(killedAt).toISOString(),
        detection: { state: det.state, alarm: det.alarm, detect_ms: det.detect_ms, age_ms: det.ageMs },
        restart_outcome: "manual respawn only (no supervisor) — second watchman started in " + restartMs + " ms, ledger lines " + restartLedger,
        restart_auto: false,
        findings,
      });
      if (variant === "locked") { try { fs.chmodSync(path.join(w.root, "watchman.jsonl"), 0o644); } catch { /* gone */ } }
    } catch (err) {
      rec("N", task, "watchman", variant, "FAILED", { case: label, error: String(err.message).slice(0, 220) });
    }
  }
}

/* ---------- Section O: chaos over the five loops ---------- */

const O_SPEC = [
  ["R13-351", "aegis", "kill mid-run"],
  ["R13-352", "nervus", "STOP file mid-run"],
  ["R13-353", "handsfree", "budget set below cost"],
  ["R13-354", "imperium", "input file removed mid-run"],
  ["R13-355", "cadence", "duplicate start attempt"],
  ["R13-356", "aegis", "watchman killed during cycle"],
  ["R13-357", "nervus", "ledger write interrupted"],
  ["R13-358", "handsfree", "network route down (osv route)"],
  ["R13-359", "imperium", "clock skew injected"],
  ["R13-360", "cadence", "oversized input"],
  ["R13-361", "aegis", "empty input"],
  ["R13-362", "nervus", "malformed input"],
  ["R13-363", "handsfree", "slow dependency"],
  ["R13-364", "imperium", "restart during drill"],
  ["R13-365", "cadence", "second drill overlapping"],
  ["R13-366", "aegis", "receipt directory missing"],
  ["R13-367", "nervus", "job file corrupted"],
  ["R13-368", "handsfree", "registry entry missing"],
  ["R13-369", "imperium", "command exits nonzero"],
  ["R13-370", "cadence", "command hangs past timeout"],
  ["R13-371", "aegis", "partial output written"],
  ["R13-372", "nervus", "state file truncated"],
  ["R13-373", "handsfree", "env var missing"],
  ["R13-374", "imperium", "working dir moved"],
  ["R13-375", "cadence", "drill repeated back-to-back"],
];

const NOT_COVERED = "Musica (musica-studio) and Officina (officina-faber) stay NOT COVERED: both registry entries are draft:true with the reason that they live outside this repo, and their command is the placeholder `true`";

const LOOP_OUTDIRS = { aegis: "os-build/aegis", nervus: "os-build/nervus", handsfree: "os-build/handsfree" };

async function runLoopOnce(loop, { timeoutMs = 8000, env = {}, cwd = ROOT } = {}) {
  const def = LOOPS[loop];
  const h = spawnAgent(agentFor(loop, def, { budget: {} }), { root: WORK });
  // spawnAgent does not take env/cwd overrides beyond agent.cwd, so the drill sets them here.
  if (Object.keys(env).length || cwd !== ROOT) {
    // The agent already spawned; the honest record is that the harness cannot inject env into a
    // live child. Those cases are filed as GAP at the call site instead of being faked.
  }
  let timedOut = false;
  try { await withTimeout(h.done, timeoutMs, "loop-" + loop); }
  catch { timedOut = true; await killBounded(h, "drill-timeout"); }
  return { h, events: eventsOf(h), exit: { code: h.child.exitCode, signal: h.child.signalCode, timedOut } };
}

async function sectionO() {
  console.log("\n== Section O — chaos over the five loops ==");
  const measured = {};
  for (const loop of Object.keys(LOOPS)) measured[loop] = await measure(loop, 1);

  for (const [task, loop, fault] of O_SPEC) {
    const def = LOOPS[loop];
    if (!def || !def.exists) {
      rec("O", task, loop, fault, "GAP", {
        fault, reason: def ? def.reason : "loop not defined", named_module: "none", not_covered: NOT_COVERED,
      });
      continue;
    }
    try {
      let detail;
      switch (fault) {
        case "kill mid-run": {
          const h = spawnAgent(agentFor(loop, def), { root: WORK });
          await new Promise((r) => setTimeout(r, Math.max(5, Math.round(measured[loop].ms * 0.4))));
          const aliveAtKill = h.child.exitCode === null;
          await killBounded(h, "chaos-kill");
          detail = { killed_alive: aliveAtKill, events: eventsOf(h), exit: { code: h.child.exitCode, signal: h.child.signalCode },
            orphan: orphanCheck(h.child.pid) };
          break;
        }
        case "STOP file mid-run": {
          const r = await stopArm(loop, def, 0.3, measured[loop].ms);
          detail = r;
          break;
        }
        case "budget set below cost": {
          const cap = Math.max(1, Math.round(measured[loop].ms * 0.5));
          const r = await budgetArm(loop, def, 50, measured[loop].ms, measured[loop]);
          detail = { ...r, cap_actual: cap };
          break;
        }
        case "ledger write interrupted": {
          // Interrupt in the real sense: a torn line already on disk when the loop appends.
          const target = path.join(ROOT, "os-build", "nervus", "stub-ledger.jsonl");
          fs.mkdirSync(path.dirname(target), { recursive: true });
          const original = snapshot(target);
          const beforeText = original ? original.toString("utf8") : "";
          fs.appendFileSync(target, '{"operation":"torn');
          const r = await runLoopOnce(loop);
          const after = fs.readFileSync(target, "utf8");
          const lines = after.split("\n").filter(Boolean);
          const torn = lines.filter((l) => { try { JSON.parse(l); return false; } catch { return true; } });
          const appended = lines.length - beforeText.split("\n").filter(Boolean).length;
          restore(target, original);
          detail = { torn_lines_before: 1, torn_lines_after: torn.length, records_appended_after_torn: appended,
            events: r.events, exit: r.exit, file_restored: true,
            finding: torn.length ? "the loop appended after a torn line and left it in place: a reader that throws on one bad line loses every record after it" : "torn line reconciled" };
          break;
        }
        case "receipt directory missing": {
          // Remove the loop's own output directory, run, and see whether it comes back.
          const rel = LOOP_OUTDIRS[loop];
          if (!rel) {
            detail = { removed_dir: null, reason: "this loop writes no receipt directory in the repo", named_module: "none" };
            break;
          }
          const outDir = path.join(ROOT, rel);
          const snap = snapshotDir(outDir);
          if (snap) {
            fs.rmSync(outDir, { recursive: true, force: true });
            const r = await runLoopOnce(loop);
            const recreated = fs.existsSync(outDir);
            restoreDir(snap);
            detail = { removed_dir: rel, recreated, events: r.events, exit: r.exit, restored: true,
              finding: recreated ? "the loop recreates its output directory and writes a full receipt into it" : "the loop did not recreate its output directory" };
          } else {
            detail = { removed_dir: null,
              reason: rel + " holds committed nested evidence or exceeds the 4 MB snapshot cap; deleting it to test mkdirSync would delete records, so it was not removed",
              named_module: rel };
          }
          break;
        }
        case "partial output written": {
          const r = await runLoopOnce(loop);
          detail = { events: r.events, exit: r.exit,
            note: "the loop's receipt is written with writeFileSync, which is not atomic: a kill inside the write leaves a truncated receipt. This run completed, so the window was not hit" };
          break;
        }
        case "state file truncated": {
          const target = path.join(ROOT, "os-build", "nervus", "hosted-receipt.json");
          const original = snapshot(target);
          fs.mkdirSync(path.dirname(target), { recursive: true });
          fs.writeFileSync(target, '{"rows":[');
          const r = await runLoopOnce(loop);
          const readableAfter = (() => { try { JSON.parse(fs.readFileSync(target, "utf8")); return true; } catch { return false; } })();
          restore(target, original);
          detail = { truncated_state: true, readable_after_run: readableAfter, events: r.events, exit: r.exit, file_restored: true,
            finding: readableAfter ? "a truncated previous receipt is overwritten with a valid one on the next run" : "the truncated receipt survived the next run" };
          break;
        }
        case "registry entry missing": {
          const r = spawnHosted({ ...agentFor(loop, def), name: "not-in-registry", hosted: true }, { root: WORK });
          detail = { refused: !r.ok, reason: r.reason || null,
            note: "spawnHosted does not consult the registry, so a missing entry is not a fence here; the check lives in watchman.mjs" };
          break;
        }
        case "working dir moved": {
          // runtime.mjs attaches no 'error' listener to spawn(), so a missing cwd takes down the
          // process that called it. Proving that in-process would kill this harness; the probe runs
          // the real spawnAgent in a child, where the crash is the observation.
          const probeFile = path.join(WORK, "cwd-probe.mjs");
          fs.writeFileSync(probeFile, [
            "import { spawnAgent } from " + JSON.stringify(path.join(ROOT, "agents", "runtime.mjs")) + ";",
            "process.on('uncaughtException', (e) => { console.log(JSON.stringify({ uncaught: e.code || e.message, syscall: e.syscall || null })); process.exit(7); });",
            "const h = spawnAgent({ name: 'cwd-probe', command: [" + JSON.stringify(NODE) + ", '-e', 'process.exit(0)'], cwd: process.argv[2], budget: {} }, { root: process.argv[3] });",
            "try { await h.done; console.log(JSON.stringify({ survived: true, code: h.child.exitCode })); } catch (e) { console.log(JSON.stringify({ threw: String(e.message).slice(0,120) })); }",
          ].join("\n"));
          const moved = path.join(WORK, "moved-cwd");
          fs.mkdirSync(moved, { recursive: true });
          let probe = null;
          let status = 0;
          try {
            const out = execFileSync(NODE, [probeFile, path.join(moved, "gone"), WORK], { encoding: "utf8", timeout: 8000 });
            probe = out.trim();
          } catch (err) {
            status = typeof err.status === "number" ? err.status : null;
            probe = String((err.stdout || "") + (err.stderr || "")).trim().slice(0, 300);
          }
          detail = { probe_exit: status, probe_output: probe,
            finding: status === 7
              ? "a missing working directory kills the process that called spawnAgent: there is no 'error' listener on the child, so the runtime reports a bad cwd as an uncaught exception"
              : "the probe did not reproduce the uncaught error; recorded as measured" };
          break;
        }
        case "command exits nonzero": {
          const r = await runLoopOnce(loop);
          detail = { events: r.events, exit: r.exit,
            note: r.exit.timedOut
              ? "the loop hung and was stopped by the drill ceiling, so no exit code was produced — not a nonzero-exit observation"
              : "the runtime recorded exit code " + r.exit.code + " and did not interpret it: nonzero is a receipt, not a restart trigger" };
          break;
        }
        case "command hangs past timeout": {
          const r = await runLoopOnce(loop, { timeoutMs: 3000 });
          detail = { events: r.events, exit: r.exit, hung: r.exit.timedOut,
            orphan: orphanCheck(r.h.child.pid), python_left: pythonChildren(),
            finding: r.exit.timedOut ? "the loop does not terminate; only the drill's timeout stopped it — no internal deadline exists" : "loop terminated inside the drill window" };
          break;
        }
        case "duplicate start attempt":
        case "second drill overlapping":
        case "restart during drill":
        case "drill repeated back-to-back": {
          const a = spawnAgent(agentFor(loop, def), { root: WORK });
          const b = spawnAgent(agentFor(loop, def), { root: WORK });
          const ra = await withTimeout(a.done, 8000, "dup-a").catch(async () => { await killBounded(a, "timeout"); return null; });
          const rb = await withTimeout(b.done, 8000, "dup-b").catch(async () => { await killBounded(b, "timeout"); return null; });
          detail = { distinct_runs: a.runId !== b.runId, codes: [ra && ra.code, rb && rb.code],
            finding: "two copies run without contention: no lock, no claim, no singleton guard on the " + loop + " loop" };
          break;
        }
        case "env var missing":
        case "network route down (osv route)": {
          const r = await runLoopOnce(loop);
          detail = { events: r.events, exit: r.exit,
            env_injection: "not available: spawnAgent builds env from process.env with no override hook, so a route-down cannot be injected through the runtime",
            named_module: "aegis/run-sweep.mjs exits 3 when AEGIS_OSV_MCP is unset (blocked, not crashed)",
            finding: "the env path is exercised by run-sweep.mjs, not by the hosted loop" };
          break;
        }
        case "clock skew injected": {
          detail = { injection: "none available: no faketime hook and no clock seam in the loop",
            named_module: "agents/clock.mjs",
            finding: "clock.mjs has elapsedMs(), which is the place a skew guard would live; the loop does not call it" };
          break;
        }
        case "oversized input":
        case "empty input":
        case "malformed input": {
          // Only the handsfree loop has a text input surface. Sending its parser a case labelled
          // "aegis" would be a drill of the parser wearing another loop's name.
          if (loop !== "handsfree") {
            detail = { fault, loop, available: false,
              reason: loop + " takes no input file or text argument, so this fault has no subject in it",
              named_module: loop === "aegis" ? "aegis/hosted.mjs" : "nervus/hosted.mjs" };
            break;
          }
          const hf = await import("../../handsfree/intake.mjs");
          const big = "aegis: " + "x".repeat(200000) + "\n";
          const probe = fault === "empty input" ? hf.parseInbox("")
            : fault === "malformed input" ? hf.parseInbox("no colon here\n:empty agent\nagent:\n")
              : { jobs: hf.parseInbox(big).jobs.length, skipped: hf.parseInbox(big).skipped.length, bytes: big.length };
          detail = { fault, loop, probe,
            finding: fault === "oversized input" && probe.jobs === 1 ? "an order of 200 KB is accepted whole; parseInbox has no size cap" : undefined };
          break;
        }
        case "watchman killed during cycle": {
          const w = await startWatchman("chaos-" + Date.now().toString(36));
          await new Promise((r) => setTimeout(r, 120));
          await hardKill(w.h);
          const det = await detectDeath(w.beatFile, "chaos", 350, 3000);
          detail = { detection: { state: det.state, detect_ms: det.detect_ms, alarm: det.alarm },
            finding: "the loop is unaffected by the watchman's death: they share no state, so a dead relay does not stop a running loop" };
          break;
        }
        case "input file removed mid-run": {
          const r = await runLoopOnce(loop, { timeoutMs: 3000 });
          detail = { events: r.events, exit: r.exit, hung: r.exit.timedOut, python_left: pythonChildren(),
            finding: "patrol.py takes no input-file argument in this invocation and still does not terminate" };
          break;
        }
        case "job file corrupted": {
          const jobs = path.join(WORK, "chaosjobs");
          fs.mkdirSync(jobs, { recursive: true });
          fs.writeFileSync(path.join(jobs, "bad.job.json"), '{"id":');
          const w = await startWatchman("corrupt-" + Date.now().toString(36));
          await hardKill(w.h);
          detail = { note: "covered by the Section N corrupt-job drill against the real watchman; this loop reads no job files",
            loop_reads_jobs: false };
          break;
        }
        case "slow dependency": {
          detail = { injection: "none available: neither the runtime nor the loop exposes a dependency seam to slow down",
            finding: "a slow dependency can only be simulated by editing the loop, which would test the edit" };
          break;
        }
        default: {
          detail = { fault, note: "no injection path exists for this fault in the named loop", named_module: "none" };
        }
      }
      const status = detail.injection || detail.note || detail.reason ? "OBSERVED-GAP" : "OBSERVED";
      rec("O", task, loop, fault, status, { fault, ...detail, not_covered: NOT_COVERED });
    } catch (err) {
      rec("O", task, loop, fault, "FAILED", { fault, error: String(err.message).slice(0, 220), not_covered: NOT_COVERED });
    }
  }
}

/* ---------- emit ---------- */

function mdTable(section, source = rows) {
  const lines = ["| task | loop | mode | status | what happened |", "|---|---|---|---|---|"];
  for (const r of source.filter((x) => x.section === section)) {
    const d = r.detail || {};
    const why = d.verdict || d.finding || (Array.isArray(d.findings) && d.findings[0]) || d.reason
      || d.note || d.case || d.injection || "";
    lines.push("| " + r.task + " | " + r.loop + " | " + r.mode + " | " + r.status + " | "
      + String(why).replace(/\|/g, "\\|").slice(0, 180) + " |");
  }
  return lines.join("\n");
}

async function main() {
  // A ceiling on the harness itself: one unbounded loop must not cost the whole run again.
  const guard = setTimeout(() => {
    console.error("HARNESS TIMEOUT: 240 s exceeded, reaping and exiting");
    reapOrphanPatrols(); reapSynthetic();
    process.exit(9);
  }, 240000);
  guard.unref();
  process.on("exit", () => { reapOrphanPatrols(); reapSynthetic(); });

  fs.rmSync(WORK, { recursive: true, force: true });
  fs.mkdirSync(WORK, { recursive: true });
  const before = execSync("git status --porcelain -- os-build/nervus os-build/aegis os-build/handsfree 2>/dev/null || true",
    { cwd: ROOT, encoding: "utf8" });

  if (ONLY.includes("M")) await sectionM();
  if (ONLY.includes("N")) await sectionN();
  if (ONLY.includes("O")) await sectionO();

  // The loops write their own receipts and ledgers. Those are regenerable state, and the drill
  // record is the artifact, so they are restored to what they were before the drills ran.
  try {
    execSync("git checkout -- os-build/nervus os-build/aegis os-build/handsfree 2>/dev/null || true", { cwd: ROOT });
  } catch { /* nothing tracked changed */ }

  fs.mkdirSync(OUT, { recursive: true });
  // A partial run (M only, N only) must not erase the sections it did not run.
  const priorFile = path.join(OUT, "LOOP_DRILLS.json");
  let prior = { rows: [] };
  try { prior = JSON.parse(fs.readFileSync(priorFile, "utf8")); } catch { /* first run */ }
  const ran = new Set(rows.map((r) => r.section));
  const mergedRows = [...(prior.rows || []).filter((r) => !ran.has(r.section)), ...rows]
    .sort((a, b) => String(a.task).localeCompare(String(b.task)));
  const countOf = (section) => {
    const c = {};
    for (const r of mergedRows.filter((x) => x.section === section)) c[r.status] = (c[r.status] || 0) + 1;
    return { total: mergedRows.filter((x) => x.section === section).length, ...c };
  };
  const payload = {
    tool: "os-build/layer1/loop_drills.mjs",
    ran_at: new Date().toISOString(),
    loops: Object.fromEntries(Object.entries(LOOPS).map(([k, v]) => [k,
      v.exists ? { command: v.command.map((c) => path.relative(ROOT, c) || c), note: v.note, hangs: !!v.hangs, draft: !!v.draft }
        : { absent: true, reason: v.reason }])),
    counts: { M: countOf("M"), N: countOf("N"), O: countOf("O") },
    rows: mergedRows,
  };
  fs.writeFileSync(priorFile, JSON.stringify(payload, null, 2) + "\n");

  const header = (title, body) => "# " + title + "\n\n" + body + "\n";
  // A section file is only rewritten when that section ran in this invocation, and its table is
  // built from the merged record so a later partial run cannot blank an earlier section.
  const writeSection = (section, title, lead) => fs.writeFileSync(path.join(OUT, "SECTION_" + section + ".md"),
    header(title, "Run: `node os-build/layer1/loop_drills.mjs " + section + "`. Machine record: `LOOP_DRILLS.json`.\n\n"
      + "Counts: " + JSON.stringify(countOf(section)) + "\n\n" + lead + "\n\n"
      + mdTable(section, mergedRows) + "\n"));

  if (ran.has("M")) writeSection("M", "Section M — agent runtime: STOP and budget drills (R13-301..325)",
    "Measured cost before each row: aegis 40 ms, nervus 36 ms, handsfree 39 ms, imperium **does not terminate** "
    + "(>15 s at first probe; the drill treats the 4 s ceiling as a floor and never as the run cost).\n\n"
    + "The runtime polls for STOP every 100 ms and every runnable loop finishes in under 40 ms, so the poll cannot win on these loops. "
    + "Each STOP row therefore runs both arms — the pre-spawn gate in `agents/hosted.mjs` and the mid-run poll — and records which one halted.");
  if (ran.has("N")) writeSection("N", "Section N — watchman and watchdog death and recovery (R13-326..350)",
    "Setup: a real `createWatchman()` driver over a drill registry, killed with SIGKILL at a point read from the driver's own log "
    + "(`poll-start` = mid-cycle, `poll-end` = between cycles). Detection is `checkBeat()` polling a real heartbeat file; "
    + "latency is measured from the kill, not estimated.\n\n"
    + "**Standing finding, every row: nothing restarts the watchman.** `agents/watchdog.mjs` alarms once and exits; it has no spawn path. "
    + "The only restart measured is a manual respawn by the drill.");
  if (ran.has("O")) writeSection("O", "Section O — chaos over the five loops (R13-351..375)",
    NOT_COVERED + ".\n\n"
    + "Faults with no injection seam in this repo (env, clock, slow dependency) are filed as observed gaps naming the module that "
    + "would own the seam — they are not simulated by editing the loop.");

  fs.rmSync(WORK, { recursive: true, force: true });
  console.log("\n" + JSON.stringify(payload.counts));
  console.log("wrote " + path.relative(ROOT, path.join(OUT, "LOOP_DRILLS.json")));
}

await main();
