// Meta OS agent layer — lessons_applied accounting (AGENTIC build order, item 4b).
//
// The Graft already lets one agent teach the crew. What it did not do is show whether a
// lesson ever changed a decision. This ledger records a citation every time a run applies a
// lesson, keyed by the lesson's timestamp. A lesson with zero citations is visible as
// untouched instead of being assumed useful.
import fs from "node:fs";
import path from "node:path";
import { lessons } from "./lessons.mjs";
import { appendLoud } from "./safe-write.mjs";

export const LESSON_OUTCOMES = ["used", "refuted", "partial"];

export class LearningError extends Error {
  constructor(code, message, detail = {}) {
    super(message);
    this.name = "LearningError";
    this.code = code;
    for (const [k, v] of Object.entries(detail)) if (!(k in this)) this[k] = v;
  }
}

function isText(value) {
  return typeof value === "string" && value.trim().length > 0;
}

export function appliedFile(root) {
  return path.join(root, "lesson-applied.jsonl");
}

function lessonKey(lesson) {
  if (lesson && typeof lesson === "object") {
    return lesson.ts || lesson.id || null;
  }
  return lesson;
}

export function recordApplied(root, { agent, lesson, outcome = "used", run = null, at = null } = {}) {
  if (!isText(agent)) throw new LearningError("agent-required", "lessons: an agent is required");
  const key = lessonKey(lesson);
  if (!isText(key)) throw new LearningError("lesson-required", "lessons: a lesson id or timestamp is required");
  if (!LESSON_OUTCOMES.includes(outcome)) {
    throw new LearningError(
      "outcome-invalid",
      "lessons: outcome must be one of " + LESSON_OUTCOMES.join(", "),
    );
  }
  const entry = {
    ts: at || new Date().toISOString(),
    agent: agent.trim(),
    lesson: String(key),
    outcome,
    run: run == null ? null : String(run),
  };
  appendLoud(appliedFile(root), JSON.stringify(entry) + "\n");
  return entry;
}

function readApplied(root) {
  let text;
  try {
    text = fs.readFileSync(appliedFile(root), "utf8");
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

export function appliedCounts(root) {
  const counts = {};
  for (const entry of readApplied(root).entries) {
    if (!isText(entry.lesson)) continue;
    counts[entry.lesson] = (counts[entry.lesson] || 0) + 1;
  }
  return counts;
}

export function appliedByAgent(root) {
  const byAgent = {};
  for (const entry of readApplied(root).entries) {
    if (!isText(entry.agent)) continue;
    byAgent[entry.agent] = (byAgent[entry.agent] || 0) + 1;
  }
  return byAgent;
}

// Join the append-only teaching record with the applied ledger. Lessons are capped at 1000
// so a long-lived crew does not read an unbounded file on every board render.
export function lessonBoard(root) {
  const counts = appliedCounts(root);
  const agents = {};
  for (const entry of readApplied(root).entries) {
    if (!isText(entry.lesson)) continue;
    agents[entry.lesson] = agents[entry.lesson] || {};
    agents[entry.lesson][entry.agent] = (agents[entry.lesson][entry.agent] || 0) + 1;
  }
  return lessons(root, 1000).map((lesson) => ({
    lesson,
    key: lesson.ts,
    applied: counts[lesson.ts] || 0,
    byAgent: agents[lesson.ts] || {},
  }));
}

export function untouchedLessons(root) {
  return lessonBoard(root).filter((row) => row.applied === 0);
}

export function learningHealth(root) {
  const { entries, torn } = readApplied(root);
  return { applied: entries.length, torn };
}
