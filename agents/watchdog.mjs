// Meta OS agent layer — the relay's watchdog (Round 8, A3).
//
// The watchman is a non-agent program with no one watching it. Its failure is silent by
// construction: no bell, no jobs, and a quiet board that looks exactly like a board with no
// work. This module is the smallest thing that makes that failure audible.
//
//   node agents/watchdog.mjs beat  [file] [limitMs]   write a heartbeat
//   node agents/watchdog.mjs check [file] [limitMs]   print the alarm line if the beat stopped
//   node agents/watchdog.mjs supervise [file] [limitMs] -- <command...>
//                                                     restart a dead watchman, once
//
// Exit codes for `check`: 0 fine, 2 dead (alarm printed once), 2 still-dead (nothing printed).
//
// ESCALATE ONCE. A checker that prints the same alarm on every run teaches everyone to ignore
// it, and the OS's own watchdog service already made this decision (WD_DEAD vs WD_STILL_DEAD).
// The raised marker is cleared by the next fresh beat, so a second outage alarms again.
import fs from "node:fs";
import path from "node:path";
import url from "node:url";
import { spawn as spawnImpl } from "node:child_process";

export const DEFAULT_MAX_AGE_MS = 15000;

export function writeBeat(file, { now = Date.now(), pid = process.pid, agent = "watchman" } = {}) {
  const tmp = file + ".tmp";
  const beat = { agent, pid, ts: now, iso: new Date(now).toISOString() };
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(tmp, JSON.stringify(beat));
  // Rename, not write-in-place: a checker must never read a half-written heartbeat and call a
  // live relay dead.
  fs.renameSync(tmp, file);
  return beat;
}

export function readBeat(file, now = Date.now()) {
  try {
    const beat = JSON.parse(fs.readFileSync(file, "utf8"));
    if (typeof beat.ts !== "number") return { beat: null, ageMs: Infinity };
    return { beat, ageMs: Math.max(0, now - beat.ts) };
  } catch {
    return { beat: null, ageMs: Infinity };
  }
}

export function alarmLine(ageMs, maxAgeMs, beat) {
  const secs = Number.isFinite(ageMs) ? (ageMs / 1000).toFixed(1) : "inf";
  const limit = (maxAgeMs / 1000).toFixed(1);
  const at = beat && beat.iso ? beat.iso : "never";
  return "ALARM watchman heartbeat lost: last beat " + secs + "s ago (limit " + limit + "s, last " + at + ")";
}

export function checkBeat(file, { maxAgeMs = DEFAULT_MAX_AGE_MS, now = Date.now(), stateFile = file + ".alarm.json" } = {}) {
  const { beat, ageMs } = readBeat(file, now);
  const fresh = beat !== null && ageMs <= maxAgeMs;

  let raised = null;
  try { raised = JSON.parse(fs.readFileSync(stateFile, "utf8")).raisedAt || null; } catch {}

  if (fresh) {
    if (raised) { try { fs.unlinkSync(stateFile); } catch {} }
    return { state: "fine", ageMs, beat, alarm: null, cleared: raised !== null };
  }

  const line = alarmLine(ageMs, maxAgeMs, beat);
  if (raised) return { state: "still-dead", ageMs, beat, alarm: null };
  fs.mkdirSync(path.dirname(stateFile), { recursive: true });
  fs.writeFileSync(stateFile, JSON.stringify({ raisedAt: new Date(now).toISOString(), ageMs }));
  return { state: beat ? "dead" : "missing", ageMs, beat, alarm: line };
}

/* ---- recovery: one bounded restart per outage, recorded (Section N) ---- */
// The alarm told a human the watchman died; nothing brought it back, so every restart in the
// drills was a hand respawn. This is the smallest recovery that is still safe: one restart per
// alarm, a fixed budget inside a window, and a jsonl line for every attempt, failed ones included.
// It never restarts a watchman whose alarm is already raised -- that bell is waiting on a human,
// and a fresh pid would hide the repeat failure.

export const DEFAULT_MAX_RESTARTS = 3;

export function readRestarts(file) {
  try {
    return fs.readFileSync(file, "utf8").split("\n").filter(Boolean).map((l) => JSON.parse(l));
  } catch {
    return [];
  }
}

export function appendRestart(file, rec) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.appendFileSync(file, JSON.stringify(rec) + "\n");
  return rec;
}

export function restartBudget(file, {
  now = Date.now(),
  windowMs = DEFAULT_MAX_AGE_MS * 10,
  maxRestarts = DEFAULT_MAX_RESTARTS,
} = {}) {
  const recent = readRestarts(file).filter(
    (r) => r && r.ok && typeof r.ts === "number" && now - r.ts <= windowMs,
  );
  return {
    used: recent.length,
    left: Math.max(0, maxRestarts - recent.length),
    windowMs,
    maxRestarts,
  };
}

export function recoverOnce({
  heartbeatFile,
  maxAgeMs = DEFAULT_MAX_AGE_MS,
  now = Date.now(),
  alarmFile = heartbeatFile + ".alarm.json",
  logFile = heartbeatFile.replace(/\.json$/, "") + ".restarts.jsonl",
  command,
  spawn = spawnImpl,
  windowMs,
  maxRestarts = DEFAULT_MAX_RESTARTS,
} = {}) {
  const check = checkBeat(heartbeatFile, { maxAgeMs, now, stateFile: alarmFile });
  if (check.state === "fine") return { restarted: false, reason: "alive", check };
  if (check.state === "still-dead") return { restarted: false, reason: "already-alarmed", check };

  const budget = restartBudget(logFile, { now, windowMs: windowMs || maxAgeMs * 10, maxRestarts });
  if (budget.left <= 0) return { restarted: false, reason: "budget-spent", check, budget };

  if (!Array.isArray(command) || command.length === 0) {
    throw new Error("recoverOnce: a restart command is required");
  }

  const at = new Date(now).toISOString();
  let child;
  try {
    child = spawn(command[0], command.slice(1), { stdio: "ignore", detached: true });
  } catch (e) {
    appendRestart(logFile, { ts: now, at, ok: false, cause: check.state, error: String(e), command });
    return { restarted: false, reason: "spawn-failed", error: String(e), check };
  }
  // A failed exec reports on 'error' asynchronously; without a listener it kills this process
  // (R13-374, exit 7 on a missing cwd). Record it instead of dying.
  if (child && typeof child.on === "function") {
    child.on("error", (e) => appendRestart(logFile, {
      ts: Date.now(), at: new Date().toISOString(), ok: false, cause: check.state,
      error: String(e), command, pid: child.pid,
    }));
  }
  if (child && typeof child.unref === "function") child.unref();
  appendRestart(logFile, {
    ts: now, at, ok: true, cause: check.state, pid: child ? child.pid : null, command,
  });
  return { restarted: true, pid: child ? child.pid : null, check, budget };
}

/* ---- CLI ---- */
const HERE = path.dirname(url.fileURLToPath(import.meta.url));
if (process.argv[1] && path.resolve(process.argv[1]) === path.resolve(url.fileURLToPath(import.meta.url))) {
  const [, , cmd, fileArg, limitArg] = process.argv;
  const file = fileArg || path.join(HERE, "watchman.heartbeat.json");
  const maxAgeMs = limitArg ? Number(limitArg) : DEFAULT_MAX_AGE_MS;
  if (cmd === "beat") {
    const b = writeBeat(file);
    console.log("beat " + b.iso);
  } else if (cmd === "check") {
    const r = checkBeat(file, { maxAgeMs });
    if (r.alarm) console.log(r.alarm);
    process.exit(r.state === "fine" ? 0 : 2);
  } else if (cmd === "supervise") {
    const sep = process.argv.indexOf("--");
    const command = sep > 0 ? process.argv.slice(sep + 1) : [];
    const r = recoverOnce({
      heartbeatFile: file,
      maxAgeMs,
      logFile: path.join(HERE, "watchman-restarts.jsonl"),
      command,
    });
    console.log(r.restarted ? "restarted watchman pid " + r.pid : "no restart: " + r.reason);
    process.exit(r.restarted ? 0 : 3);
  } else {
    console.error("usage: watchdog.mjs beat|check [file] [limitMs] | supervise [file] [limitMs] -- <command...>");
    process.exit(1);
  }
}
