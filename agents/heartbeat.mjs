// Meta OS agent layer — daily heartbeat record (R2-T3 patrol lane, task 67).
//
// The scheduler ran is only a claim until a record says so. beatDaily appends
// one JSONL record per UTC day to <dir>/heartbeat.jsonl: {date, ts, iso,
// commit, scheduler}. Calling it twice on the same day writes once
// (idempotent); a new UTC day writes a new line. It never touches the network.
//
//   node agents/heartbeat.mjs --dir DIR [--scheduler NAME] [--commit SHA]
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import url from "node:url";
import { execSync } from "node:child_process";

export function defaultDataDir() {
  if (process.env.R2T3_DATA_DIR) return path.resolve(process.env.R2T3_DATA_DIR);
  const base = process.env.XDG_STATE_HOME || path.join(os.homedir(), ".local", "state");
  return path.join(base, "oc2-agent-r2t3-d");
}

export function heartbeatFile(dir) {
  return path.join(dir, "heartbeat.jsonl");
}

export function utcDate(ms) {
  return new Date(ms).toISOString().slice(0, 10);
}

export function gitCommit(repoRoot) {
  try {
    return execSync("git rev-parse HEAD", { cwd: repoRoot, encoding: "utf8" }).trim();
  } catch {
    return "unknown";
  }
}

export function readBeats(dir) {
  const file = heartbeatFile(dir);
  if (!fs.existsSync(file)) return [];
  const out = [];
  for (const line of fs.readFileSync(file, "utf8").split("\n")) {
    if (!line.trim()) continue;
    try {
      out.push(JSON.parse(line));
    } catch {
      // A torn tail line is skipped like the runtime ledger: one bad line
      // must not hide the days that recorded fine.
    }
  }
  return out;
}

// One record per UTC day. Returns {written, record, path}: written=false when
// today's line is already there (the scheduler ticking twice is normal).
export function beatDaily({ dir, now = Date.now(), scheduler = "oc2-eval.timer", commit = null, repoRoot = null } = {}) {
  if (!dir) throw new Error("heartbeat: dir is required");
  fs.mkdirSync(dir, { recursive: true });
  const date = utcDate(now);
  const beats = readBeats(dir);
  const existing = beats.find((b) => b && b.date === date);
  if (existing) return { written: false, record: existing, path: heartbeatFile(dir) };
  const record = {
    date,
    ts: now,
    iso: new Date(now).toISOString(),
    commit: commit || (repoRoot ? gitCommit(repoRoot) : "unknown"),
    scheduler,
  };
  fs.appendFileSync(heartbeatFile(dir), JSON.stringify(record) + "\n");
  return { written: true, record, path: heartbeatFile(dir) };
}

/* ---- CLI ---- */
const HERE = path.dirname(url.fileURLToPath(import.meta.url));
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
  const dir = path.resolve(arg("--dir", defaultDataDir()));
  const out = beatDaily({ dir, scheduler: arg("--scheduler", "oc2-eval.timer"), repoRoot: path.dirname(HERE) });
  console.log(JSON.stringify({ ...out, dir }, null, 2));
}
