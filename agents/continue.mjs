// Meta OS agent layer — the continue outcome (AGENTIC build order, item 4c).
//
// A job that stops mid-way has two honest choices: hand off a baton, or say "continue me".
// The second one is dangerous if it is unbounded — an agent that always asks for one more
// slice is a loop with a heartbeat. This file makes the request explicit and bounds it on
// cycles, wall clock, cost, exit code, and the STOP file. The request is claimed by rename,
// so two relays cannot both continue the same run.
import fs from "node:fs";
import path from "node:path";
import { writeFileLoud, writeIfChanged } from "./safe-write.mjs";

export const CONTINUE_FILE = "continue.json";
export const DEFAULT_MAX_CONTINUES = 4;

export class ContinueError extends Error {
  constructor(code, message, detail = {}) {
    super(message);
    this.name = "ContinueError";
    this.code = code;
    for (const [k, v] of Object.entries(detail)) if (!(k in this)) this[k] = v;
  }
}

function isText(value) {
  return typeof value === "string" && value.trim().length > 0;
}

function validateBaton(baton) {
  if (baton == null) return;
  if (typeof baton !== "object" || Array.isArray(baton)) {
    throw new ContinueError("continue-malformed", "continue: baton must be an object");
  }
  if (!Number.isInteger(baton.stepIndex) || baton.stepIndex < -1) {
    throw new ContinueError("continue-malformed", "continue: baton.stepIndex must be an integer >= -1");
  }
  for (const field of ["state", "nextStep"]) {
    if (baton[field] != null && typeof baton[field] !== "string") {
      throw new ContinueError("continue-malformed", "continue: baton." + field + " must be a string");
    }
  }
  if (baton.artifacts != null && !Array.isArray(baton.artifacts)) {
    throw new ContinueError("continue-malformed", "continue: baton.artifacts must be an array");
  }
}

export function validateContinue(request) {
  const errors = [];
  const err = (field, message) => errors.push({ field, message });
  if (!request || typeof request !== "object" || Array.isArray(request)) {
    return { ok: false, errors: [{ field: "$", message: "continue request must be an object" }] };
  }
  if (request.outcome !== "continue") err("outcome", "outcome must be \"continue\"");
  if (!isText(request.reason)) err("reason", "reason is required");
  if (!isText(request.next)) err("next", "next is required — continuation needs an order");
  try {
    validateBaton(request.baton);
  } catch (error) {
    err("baton", error.message.replace(/^continue:\s*/, ""));
  }
  return { ok: errors.length === 0, errors };
}

export function writeContinue(runDir, request = {}) {
  const candidate = {
    outcome: "continue",
    reason: request.reason,
    next: request.next,
    baton: request.baton == null ? null : request.baton,
    estimatedCostUsd: request.estimatedCostUsd,
    requested_at: request.requested_at || new Date().toISOString(),
  };
  const verdict = validateContinue(candidate);
  if (!verdict.ok) {
    throw new ContinueError(
      "continue-malformed",
      "continue: " + verdict.errors.map((e) => e.field + ": " + e.message).join("; "),
      { errors: verdict.errors },
    );
  }
  fs.mkdirSync(runDir, { recursive: true });
  writeFileLoud(path.join(runDir, CONTINUE_FILE), JSON.stringify(candidate, null, 2) + "\n");
  return candidate;
}

export function readContinue(runDir) {
  let text;
  try {
    text = fs.readFileSync(path.join(runDir, CONTINUE_FILE), "utf8");
  } catch {
    return null;
  }
  let request;
  try {
    request = JSON.parse(text);
  } catch (err) {
    throw new ContinueError("continue-malformed", "continue: unreadable request in " + runDir + ": " + err.message);
  }
  const verdict = validateContinue(request);
  if (!verdict.ok) {
    throw new ContinueError(
      "continue-malformed",
      "continue: " + verdict.errors.map((e) => e.field + ": " + e.message).join("; "),
      { errors: verdict.errors },
    );
  }
  return request;
}

// Exactly-once claiming by rename. If two watchmen see the same request, one rename wins
// and the other gets null.
export function claimContinue(runDir) {
  const request = readContinue(runDir);
  if (!request) return null;
  const archived = path.join(
    runDir,
    "continue.claimed." + Date.now() + "." + process.pid + ".json",
  );
  try {
    fs.renameSync(path.join(runDir, CONTINUE_FILE), archived);
  } catch (err) {
    if (err && err.code === "ENOENT") return null;
    throw err;
  }
  return { request, archived };
}

// All the reasons not to continue, in the order they should win. A refusal is a result,
// not an exception: the watchman records it and moves on.
export function continueDecision(runDir, options = {}) {
  const request = readContinue(runDir);
  if (!request) return { continue: false, reason: "no-request", request: null };

  if (options.stopFileExists === true || fs.existsSync(path.join(runDir, "STOP"))) {
    return { continue: false, reason: "stop-file", request };
  }
  if (options.exitCode != null && options.exitCode !== 0) {
    return { continue: false, reason: "nonzero-exit", exitCode: options.exitCode, request };
  }

  const cycles = options.cycles == null ? 0 : Number(options.cycles);
  const maxContinues = options.maxContinues == null ? DEFAULT_MAX_CONTINUES : Number(options.maxContinues);
  if (!Number.isInteger(cycles) || cycles < 0) {
    throw new ContinueError("cycles-invalid", "continue: cycles must be a non-negative integer");
  }
  if (!Number.isInteger(maxContinues) || maxContinues < 0) {
    throw new ContinueError("max-invalid", "continue: maxContinues must be a non-negative integer");
  }
  if (cycles >= maxContinues) {
    return { continue: false, reason: "continue-cap", cycles, maxContinues, request };
  }

  if (options.maxWallMs != null) {
    const elapsed = options.elapsedMs == null ? 0 : Number(options.elapsedMs);
    if (!Number.isFinite(elapsed) || elapsed < 0) {
      throw new ContinueError("elapsed-invalid", "continue: elapsedMs must be a non-negative number");
    }
    if (elapsed >= Number(options.maxWallMs)) {
      return { continue: false, reason: "wall-cap", elapsedMs: elapsed, capMs: Number(options.maxWallMs), request };
    }
  }

  if (options.maxCostUsd != null) {
    const spent = options.costUsd == null ? 0 : Number(options.costUsd);
    if (!Number.isFinite(spent) || spent < 0) {
      throw new ContinueError("cost-invalid", "continue: costUsd must be a non-negative number");
    }
    if (spent >= Number(options.maxCostUsd)) {
      return { continue: false, reason: "cost-cap", costUsd: spent, capUsd: Number(options.maxCostUsd), request };
    }
  }

  return { continue: true, reason: null, request };
}

function safeId(value) {
  return String(value).replace(/[^a-zA-Z0-9._-]/g, "_");
}

// The next job is a continuation of the same logical job, with a new id so the relay's
// claim set treats it as new work. The logical job id survives in `parentJobId`.
export function continueJob({ job, runId, request, cycles = 0 } = {}) {
  if (!job || !isText(job.id)) throw new ContinueError("job-required", "continue: a job with an id is required");
  if (!isText(runId)) throw new ContinueError("run-required", "continue: a run id is required");
  const verdict = validateContinue(request);
  if (!verdict.ok) throw new ContinueError("continue-malformed", "continue: invalid request");
  const n = Number(cycles) + 1;
  if (!Number.isInteger(n) || n < 1) {
    throw new ContinueError("cycles-invalid", "continue: cycles must be a non-negative integer");
  }
  return {
    id: safeId(job.id) + "~c" + n + "-" + safeId(runId),
    parentJobId: job.id,
    agent: job.agent,
    orders:
      "Continuation " + n + " of job " + job.id + " — the previous run stopped on purpose and asked for the next slice.\n" +
      "Reason: " + request.reason + "\n" +
      "Next: " + request.next + "\n" +
      "Do not restart; continue from the state the previous run left.",
    continuesFrom: runId,
    continueCycles: n,
    maxContinues: job.maxContinues == null ? DEFAULT_MAX_CONTINUES : job.maxContinues,
    baton: request.baton || null,
    estimatedCostUsd: request.estimatedCostUsd,
  };
}

// Deterministic filename + writeIfChanged makes queueing idempotent: a relay that crashes
// after writing the job and before archiving the request writes the same bytes on retry.
export function writeContinueJob(jobsDir, job) {
  if (!job || !isText(job.id)) throw new ContinueError("job-required", "continue: a job with an id is required");
  fs.mkdirSync(jobsDir, { recursive: true });
  const file = path.join(jobsDir, job.id + ".job.json");
  return writeIfChanged(file, JSON.stringify(job, null, 2) + "\n");
}
