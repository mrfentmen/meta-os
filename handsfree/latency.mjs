// Hands-Free C6 — the order-to-brief latency record (R11-246).
//
// The number is computed from two records the host actually wrote: the job file's `filedAt` and
// the result file's `finishedAt`. There is no timer around the agent's work here; a stopwatch in
// this process would measure the stopwatch. A clock that jumped backwards yields 0 ms plus
// `clockJump: true`, never a negative duration that reads as "faster than possible".
import fs from "node:fs";
import path from "node:path";
import { elapsedMs } from "../agents/clock.mjs";
import { appendLoud } from "../agents/safe-write.mjs";

export function latencyOf({ filedAt, finishedAt }) {
  const start = Date.parse(filedAt);
  const end = Date.parse(finishedAt);
  if (!Number.isFinite(start) || !Number.isFinite(end)) {
    return { ok: false, reason: "unreadable-timestamp", filedAt, finishedAt };
  }
  const e = elapsedMs(start, end);
  return { ok: true, ms: e.ms, filedAt, finishedAt, clockJump: e.jumped, reason: e.reason };
}

// Read a job board pair and measure every job that has both halves.
export function measureBoard(jobsDir, resultDir = jobsDir) {
  const out = [];
  if (!fs.existsSync(jobsDir) || !fs.existsSync(resultDir)) return out;
  for (const f of fs.readdirSync(jobsDir).filter((x) => x.endsWith(".job.json")).sort()) {
    const id = f.replace(/\.job\.json$/, "");
    const resultFile = path.join(resultDir, id + ".result.json");
    if (!fs.existsSync(resultFile)) continue;
    let job, res;
    try { job = JSON.parse(fs.readFileSync(path.join(jobsDir, f), "utf8")); } catch { continue; }
    try { res = JSON.parse(fs.readFileSync(resultFile, "utf8")); } catch { continue; }
    if (!job.filedAt || !res.finishedAt) continue;
    out.push({ id, agent: job.agent, ...latencyOf({ filedAt: job.filedAt, finishedAt: res.finishedAt }) });
  }
  return out;
}

export function fileLatency(file, rows) {
  const ok = rows.filter((r) => r.ok);
  const ms = ok.map((r) => r.ms).sort((a, b) => a - b);
  const summary = {
    measured: ok.length,
    skipped: rows.length - ok.length,
    minMs: ms.length ? ms[0] : null,
    medianMs: ms.length ? ms[Math.floor(ms.length / 2)] : null,
    maxMs: ms.length ? ms[ms.length - 1] : null,
    clockJumps: ok.filter((r) => r.clockJump).length,
    at: new Date().toISOString(),
    rows,
  };
  appendLoud(file, JSON.stringify(summary) + "\n");
  return summary;
}
