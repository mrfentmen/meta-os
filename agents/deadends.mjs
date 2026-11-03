// Meta OS agent layer — dead ends (AGENTIC build order, item 4a).
//
// A crew that forgets a failed approach will try it again, with confidence, and pay for it
// twice. This store is append-only and keyed by a normalized task signature plus the
// approach. Recording the same dead end twice is a no-op, not a second lesson. Retrying one
// requires an explicit override that is itself recorded.
import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { appendLoud, writeFileLoud } from "./safe-write.mjs";

export class DeadEndError extends Error {
  constructor(code, message, detail = {}) {
    super(message);
    this.name = "DeadEndError";
    this.code = code;
    for (const [k, v] of Object.entries(detail)) if (!(k in this)) this[k] = v;
  }
}

function isText(value) {
  return typeof value === "string" && value.trim().length > 0;
}

export function deadEndFile(root) {
  return path.join(root, "deadends.jsonl");
}

export function normalizeTask(task) {
  if (!isText(task)) throw new DeadEndError("task-required", "dead end: a task is required");
  return task.toLowerCase().replace(/\s+/g, " ").trim();
}

// The signature deliberately ignores case and whitespace: "Fix  the Flaky Test" and
// "fix the flaky test" are the same job, and a dead end must not be lost to formatting.
export function taskSignature(task) {
  return crypto.createHash("sha256").update(normalizeTask(task)).digest("hex").slice(0, 16);
}

function approachKey(approach) {
  return approach.toLowerCase().replace(/\s+/g, " ").trim();
}

function readAll(root) {
  let text;
  try {
    text = fs.readFileSync(deadEndFile(root), "utf8");
  } catch {
    return { entries: [], torn: 0 };
  }
  const entries = [];
  let torn = 0;
  for (const line of text.split("\n")) {
    if (!line) continue;
    try {
      entries.push(JSON.parse(line));
    } catch {
      torn += 1;
    }
  }
  return { entries, torn };
}

export function recordDeadEnd(root, { task, approach, why_failed, evidence, at = null } = {}) {
  if (!isText(task)) throw new DeadEndError("task-required", "dead end: a task is required");
  if (!isText(approach)) throw new DeadEndError("approach-required", "dead end: an approach is required");
  if (!isText(why_failed)) throw new DeadEndError("reason-required", "dead end: why_failed is required");
  if (!isText(evidence)) {
    throw new DeadEndError("evidence-required", "dead end: evidence is required — a hunch is not a dead end");
  }
  const signature = taskSignature(task);
  const key = approachKey(approach);
  const prior = readAll(root).entries.find(
    (entry) => !entry.kind && entry.signature === signature && approachKey(entry.approach) === key,
  );
  if (prior) return { recorded: false, duplicate: true, prior, signature };
  const entry = {
    ts: at || new Date().toISOString(),
    task: normalizeTask(task),
    signature,
    approach: approach.trim(),
    why_failed: why_failed.trim(),
    evidence: evidence.trim(),
  };
  appendLoud(deadEndFile(root), JSON.stringify(entry) + "\n");
  return { recorded: true, duplicate: false, entry, signature };
}

export function findDeadEnd(root, { task, approach } = {}) {
  if (!isText(task)) throw new DeadEndError("task-required", "dead end: a task is required");
  if (!isText(approach)) throw new DeadEndError("approach-required", "dead end: an approach is required");
  const signature = taskSignature(task);
  const key = approachKey(approach);
  return (
    readAll(root).entries.find(
      (entry) => !entry.kind && entry.signature === signature && approachKey(entry.approach) === key,
    ) || null
  );
}

// Call before attempting an approach. A known dead end throws unless the caller supplies a
// reason for retrying; the override is appended so the exception is visible to the crew.
export function assertFresh(root, { task, approach, override = null } = {}) {
  const prior = findDeadEnd(root, { task, approach });
  if (!prior) return { ok: true, prior: null, override: false };
  if (override != null) {
    if (!isText(override)) {
      throw new DeadEndError("override-reason-required", "dead end: an override needs a reason");
    }
    const entry = {
      kind: "override",
      ts: new Date().toISOString(),
      task: prior.task,
      signature: prior.signature,
      approach: prior.approach,
      reason: override.trim(),
      prior_ts: prior.ts,
    };
    appendLoud(deadEndFile(root), JSON.stringify(entry) + "\n");
    return { ok: true, prior, override: true, entry };
  }
  throw new DeadEndError(
    "known-dead-end",
    "dead end: \"" + prior.approach + "\" already failed (" + prior.why_failed + "); pass an override reason to retry",
    { prior },
  );
}

export function deadEnds(root, { task = null, signature = null, limit = 50 } = {}) {
  if (!Number.isInteger(limit) || limit < 1) {
    throw new DeadEndError("limit-invalid", "dead end: limit must be a positive integer");
  }
  const wanted = signature || (task ? taskSignature(task) : null);
  const { entries, torn } = readAll(root);
  const filtered = entries.filter((entry) => !wanted || entry.signature === wanted);
  return { entries: filtered.slice(-limit), torn, total: filtered.length };
}

export function deadEndStats(root) {
  const { entries, torn } = readAll(root);
  const original = entries.filter((entry) => !entry.kind);
  const byApproach = {};
  const byTask = {};
  for (const entry of original) {
    byApproach[entry.approach] = (byApproach[entry.approach] || 0) + 1;
    byTask[entry.signature] = (byTask[entry.signature] || 0) + 1;
  }
  return {
    total: original.length,
    overrides: entries.filter((entry) => entry.kind === "override").length,
    torn,
    byApproach,
    byTask,
  };
}

// A compact block for a spawn brief or continuation order.
export function renderDeadEnds(root, { task, limit = 10 } = {}) {
  const { entries } = deadEnds(root, { task, limit });
  if (entries.length === 0) return "Known dead ends: none recorded for this task.";
  const lines = ["Known dead ends (do not retry without a recorded override):"];
  for (const entry of entries) {
    if (entry.kind === "override") lines.push("- override: " + entry.approach + " — " + entry.reason);
    else lines.push("- " + entry.approach + " — " + entry.why_failed + " (evidence: " + entry.evidence.slice(0, 200) + ")");
  }
  return lines.join("\n");
}

export function deadEndsHealth(root) {
  const { entries, torn } = readAll(root);
  return { good: entries.length, torn };
}

// Keep the import of writeFileLoud meaningful for callers that want to seed a store from a
// fixture; the store itself is append-only and never rewritten.
export function seedDeadEnds(root, entries) {
  if (!Array.isArray(entries)) throw new DeadEndError("seed-invalid", "dead end: seed must be an array");
  const lines = entries.map((entry) => JSON.stringify(entry)).join("\n");
  writeFileLoud(deadEndFile(root), lines ? lines + "\n" : "");
  return entries.length;
}
