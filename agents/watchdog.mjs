// Meta OS agent layer — the relay's watchdog (Round 8, A3).
//
// The watchman is a non-agent program with no one watching it. Its failure is silent by
// construction: no bell, no jobs, and a quiet board that looks exactly like a board with no
// work. This module is the smallest thing that makes that failure audible.
//
//   node agents/watchdog.mjs beat  [file] [limitMs]   write a heartbeat
//   node agents/watchdog.mjs check [file] [limitMs]   print the alarm line if the beat stopped
//
// Exit codes for `check`: 0 fine, 2 dead (alarm printed once), 2 still-dead (nothing printed).
//
// ESCALATE ONCE. A checker that prints the same alarm on every run teaches everyone to ignore
// it, and the OS's own watchdog service already made this decision (WD_DEAD vs WD_STILL_DEAD).
// The raised marker is cleared by the next fresh beat, so a second outage alarms again.
import fs from "node:fs";
import path from "node:path";
import url from "node:url";

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
  } else {
    console.error("usage: watchdog.mjs beat [file] [limitMs] | check [file] [limitMs]");
    process.exit(1);
  }
}
