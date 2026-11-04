// Meta OS agent layer — stale-run cleanup (R2-T3 eval lane, task 79).
//
// A run older than maxAgeMs with no exit marker is abandoned, not deleted:
// the run dir stays (audit trail), and two records say so —
//   runs/<id>/abandoned.json   {run, startedAt, markedAt, ageMs, reason}
//   a "run-abandoned" line in runs/<id>/ledger.jsonl
// so a later reader can tell "died a day ago, marked" from "still going".
//
// Completion markers (any one counts as finished):
//   runs/<id>/end.json exists, or the run ledger holds an "exit" event.
// Start time: runs/<id>/start.json {startedAt}, else the earliest ledger ts,
// else the run dir mtime. Runs with no determinable start are left alone and
// named in the returned skipped list — guessing is how live runs get buried.
//
//   node agents/cleanup.mjs --root DIR [--max-age-hours 24] [--json]
import fs from "node:fs";
import path from "node:path";
import url from "node:url";

export const DEFAULT_MAX_AGE_MS = 24 * 3600 * 1000;

export function runStartMs(runDir) {
  try {
    const s = JSON.parse(fs.readFileSync(path.join(runDir, "start.json"), "utf8"));
    const t = Date.parse(s.startedAt);
    if (Number.isFinite(t)) return t;
  } catch { /* fall through */ }
  try {
    let earliest = Infinity;
    for (const line of fs.readFileSync(path.join(runDir, "ledger.jsonl"), "utf8").split("\n")) {
      if (!line.trim()) continue;
      const t = Date.parse(JSON.parse(line).ts);
      if (Number.isFinite(t) && t < earliest) earliest = t;
    }
    if (earliest !== Infinity) return earliest;
  } catch { /* fall through */ }
  try {
    const st = fs.statSync(runDir);
    if (st.mtimeMs) return st.mtimeMs;
  } catch { /* unstatable */ }
  return null;
}

export function runFinished(runDir) {
  if (fs.existsSync(path.join(runDir, "end.json"))) return true;
  try {
    for (const line of fs.readFileSync(path.join(runDir, "ledger.jsonl"), "utf8").split("\n")) {
      if (!line.trim()) continue;
      try {
        if (JSON.parse(line).event === "exit") return true;
      } catch { /* torn line is not an exit */ }
    }
  } catch { /* no ledger: not finished */ }
  return false;
}

// Marks every stale run; returns {marked, skipped, live}.
export function cleanupStaleRuns({ root, now = Date.now(), maxAgeMs = DEFAULT_MAX_AGE_MS } = {}) {
  if (!root) throw new Error("cleanup: root is required");
  const runsDir = path.join(root, "runs");
  const out = { marked: [], skipped: [], live: [] };
  let ids = [];
  try {
    ids = fs.readdirSync(runsDir).filter((n) => {
      try {
        return fs.statSync(path.join(runsDir, n)).isDirectory();
      } catch {
        return false;
      }
    }).sort();
  } catch {
    return out; // no runs dir: nothing to clean
  }
  for (const id of ids) {
    const runDir = path.join(runsDir, id);
    if (runFinished(runDir)) continue;
    const start = runStartMs(runDir);
    if (start === null) {
      out.skipped.push({ run: id, reason: "no determinable start" });
      continue;
    }
    const ageMs = now - start;
    if (ageMs < maxAgeMs) {
      out.live.push({ run: id, ageMs });
      continue;
    }
    const marker = {
      run: id,
      startedAt: new Date(start).toISOString(),
      markedAt: new Date(now).toISOString(),
      ageMs,
      reason: "stale-run",
    };
    fs.writeFileSync(path.join(runDir, "abandoned.json"), JSON.stringify(marker, null, 2));
    try {
      fs.appendFileSync(
        path.join(runDir, "ledger.jsonl"),
        JSON.stringify({ ts: new Date(now).toISOString(), run: id, event: "run-abandoned", ageMs }) + "\n"
      );
    } catch { /* the marker file is the record; the ledger line is a bonus */ }
    out.marked.push(marker);
  }
  return out;
}

/* ---- CLI ---- */
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
  const root = path.resolve(arg("--root", process.cwd()));
  const out = cleanupStaleRuns({
    root,
    maxAgeMs: Number(arg("--max-age-hours", "24")) * 3600 * 1000,
  });
  if (process.argv.includes("--json")) console.log(JSON.stringify(out, null, 2));
  else {
    for (const m of out.marked) console.log("abandoned " + m.run + " age " + Math.round(m.ageMs / 3600000) + "h");
    for (const s of out.skipped) console.log("skipped " + s.run + ": " + s.reason);
    console.log(`${out.marked.length} abandoned, ${out.skipped.length} skipped, ${out.live.length} live`);
  }
}
