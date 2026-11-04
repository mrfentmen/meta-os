// Conversation threads: one append-only file per room, so the desk remembers.
//
// The chat box used to forget everything the moment the panel closed. A thread
// here is a name, a directory and a file of NDJSON lines — nothing else:
//
//   {at, role: "operator" | "bot" | "error", bot, text}
//
// Appending is the only write. A line is never edited or deleted, so a
// transcript cannot be rewritten by a later turn, and a failed model call
// leaves a line saying it failed rather than a question with no record of what
// happened to it.
//
// Thread ids come from the page (so a reload lands in the same room), which
// makes them untrusted input: validThreadId is the only door, and everything
// else is refused instead of being resolved against the state directory.

import fs from "node:fs";
import path from "node:path";

export const MAX_TURN_CHARS = 4000;
export const DEFAULT_READ_LIMIT = 40;
const THREAD_ID = /^[a-z0-9][a-z0-9_-]{0,63}$/;

export function validThreadId(id) {
  return typeof id === "string" && THREAD_ID.test(id);
}

export function threadDir(dir) {
  return path.join(dir, "threads");
}

export function threadPath(dir, id) {
  if (!validThreadId(id)) throw new Error(`thread id must match ${THREAD_ID}`);
  return path.join(threadDir(dir), `${id}.ndjson`);
}

function clip(text) {
  const s = typeof text === "string" ? text : String(text ?? "");
  return s.length > MAX_TURN_CHARS ? `${s.slice(0, MAX_TURN_CHARS)}…` : s;
}

export function appendTurn(dir, id, turn) {
  const file = threadPath(dir, id);
  const role = turn && turn.role;
  if (!["operator", "bot", "error"].includes(role)) {
    throw new Error('turn role must be "operator", "bot" or "error"');
  }
  const text = clip(turn.text);
  if (!text.trim()) throw new Error("turn text must not be empty");
  const line = JSON.stringify({
    at: new Date().toISOString(),
    role,
    bot: typeof turn.bot === "string" && turn.bot ? turn.bot : null,
    text,
  });
  fs.mkdirSync(threadDir(dir), { recursive: true, mode: 0o700 });
  // The file is created 0600 for the same reason the bus token is: a
  // transcript holds whatever the operator typed at their desk.
  fs.appendFileSync(file, `${line}\n`, { mode: 0o600 });
  return { file, line: JSON.parse(line) };
}

export function readThread(dir, id, limit = DEFAULT_READ_LIMIT) {
  const file = threadPath(dir, id);
  let raw;
  try {
    raw = fs.readFileSync(file, "utf8");
  } catch (err) {
    if (err && err.code === "ENOENT") return { turns: [], skipped: 0 };
    throw err;
  }
  const turns = [];
  let skipped = 0;
  for (const line of raw.split("\n")) {
    if (!line.trim()) continue;
    try {
      const parsed = JSON.parse(line);
      if (!parsed || typeof parsed.text !== "string") throw new Error("no text");
      turns.push({
        at: parsed.at,
        role: parsed.role,
        bot: parsed.bot ?? null,
        text: parsed.text,
      });
    } catch {
      // A half-written last line (the process died mid-append) must not hide
      // the whole transcript; count it and move on.
      skipped += 1;
    }
  }
  const capped = Number.isFinite(limit) && limit > 0 ? Math.floor(limit) : DEFAULT_READ_LIMIT;
  return { turns: turns.slice(-capped), skipped, total: turns.length };
}

export function listThreads(dir) {
  try {
    return fs
      .readdirSync(threadDir(dir))
      .filter((f) => f.endsWith(".ndjson"))
      .map((f) => ({ id: f.replace(/\.ndjson$/, ""), bytes: fs.statSync(path.join(threadDir(dir), f)).size }))
      .sort((a, b) => a.id.localeCompare(b.id));
  } catch (err) {
    if (err && err.code === "ENOENT") return [];
    throw err;
  }
}

// The room as the model sees it: who said what, clipped, newest kept. This is
// a transcript block rather than fake assistant turns, because one thread can
// hold several bots and pretending each one is "the assistant" would tell the
// model it wrote lines it did not write.
export function formatTranscript(turns, maxChars = 3000) {
  const rows = [];
  for (const turn of turns || []) {
    const who =
      turn.role === "operator"
        ? "operator"
        : turn.role === "error"
          ? "system"
          : (turn.bot || "agent");
    const label = who.charAt(0).toUpperCase() + who.slice(1);
    rows.push(`${label}: ${turn.text.replace(/\s+/g, " ").trim()}`);
  }
  const kept = [];
  let total = 0;
  for (let i = rows.length - 1; i >= 0; i -= 1) {
    const row = rows[i];
    if (total + row.length + 1 > maxChars && kept.length) break;
    kept.unshift(row);
    total += row.length + 1;
  }
  return kept.join("\n");
}
