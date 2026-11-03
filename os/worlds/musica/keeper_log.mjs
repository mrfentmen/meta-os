// Musica keeper records — the overnight window, read from a real take log.
//
// A session's take log is one JSON line per take, in the order the takes
// happened. This module turns those lines into the record a later reader asks
// for: when the session started, when it ended, and how many takes it kept. It
// computes nothing the log does not already carry — a missing timestamp stays
// missing, and the record says it is incomplete rather than filling it in.

function parseTime(value) {
  if (typeof value !== "string" || value.trim() === "") return null;
  const t = Date.parse(value);
  return Number.isNaN(t) ? null : { iso: value, ms: t };
}

/**
 * One keeper window from a take log.
 * Returns {session, start, end, kept, rejected, takes, complete, missing}.
 * `complete` is false when any take has no usable timestamp or verdict; the
 * missing fields are named in `missing` rather than guessed.
 */
export function keeperWindow(takes, { session } = {}) {
  if (!Array.isArray(takes) || takes.length === 0) {
    throw new Error("keeper log: at least one take is required");
  }

  const missing = new Set();
  let first = null;
  let last = null;
  let kept = 0;
  let rejected = 0;

  for (const take of takes) {
    const at = parseTime(take && take.timestamp);
    if (!at) missing.add("timestamp");
    else {
      if (!first || at.ms < first.ms) first = at;
      if (!last || at.ms > last.ms) last = at;
    }

    if (take && take.verdict === "keeper") kept++;
    else if (take && typeof take.verdict === "string" && take.verdict !== "") rejected++;
    else missing.add("verdict");
  }

  const id = session || (takes[0] && takes[0].session_id) || null;
  if (!id) missing.add("session");

  return {
    session: id,
    start: first ? first.iso : null,
    end: last ? last.iso : null,
    kept,
    rejected,
    takes: takes.length,
    complete: missing.size === 0,
    missing: [...missing],
  };
}

/** The same window as one JSONL line, in the order the fields are declared. */
export function keeperLine(window) {
  return JSON.stringify(window);
}

/**
 * Read a keeper log back, flagging an entry that has no end field — an
 * interrupted session — instead of treating it as a finished one.
 */
export function validateKeeperEntry(entry) {
  const errors = [];
  if (!entry || typeof entry !== "object") return ["keeper entry: must be an object"];
  if (!entry.session) errors.push("session: required");
  if (!entry.start) errors.push("start: required");
  if (!entry.end) errors.push("end: missing — the session did not record its finish");
  if (entry.end && entry.start && Date.parse(entry.end) < Date.parse(entry.start)) {
    errors.push("end: is before start");
  }
  if (!Number.isInteger(entry.kept) || entry.kept < 0) errors.push("kept: must be a non-negative integer");
  if (!Number.isInteger(entry.takes) || entry.takes < 0) errors.push("takes: must be a non-negative integer");
  if (Number.isInteger(entry.kept) && Number.isInteger(entry.takes) && entry.kept > entry.takes) {
    errors.push("kept: more keepers than takes");
  }
  return errors;
}
