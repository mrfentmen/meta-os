// Meta Aegis — D5, the findings lifecycle (R11-236).
//
// One append-only file, three events: open, acknowledge, close. State is derived by replay, so
// there is no field that can disagree with the events that produced it. The refusals are the
// point: a close without an acknowledgement is refused, a second close is refused, and an id
// nobody opened cannot be acted on. Every refusal is a record too, not a thrown error nobody sees.
import fs from "node:fs";
import path from "node:path";

export const EVENTS = ["open", "acknowledge", "close"];

export class LifecycleError extends Error {}

function append(file, rec) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.appendFileSync(file, JSON.stringify(rec) + "\n");
  return rec;
}

function read(file) {
  if (!fs.existsSync(file)) return { events: [], torn: 0 };
  const events = [];
  let torn = 0;
  for (const line of fs.readFileSync(file, "utf8").split("\n")) {
    if (!line) continue;
    try { events.push(JSON.parse(line)); } catch { torn += 1; }
  }
  return { events, torn };
}

export function stateOf(events, id) {
  let state = "unknown";
  for (const e of events) {
    if (e.id !== id) continue;
    if (e.event === "open") state = "open";
    else if (e.event === "acknowledge") state = "acknowledged";
    else if (e.event === "close") state = "closed";
    else if (e.event === "refused") state = state;   // a refusal never moves the state
  }
  return state;
}

export function openFinding(file, { id, title, severity = "low", by = "aegis", now = () => new Date() }) {
  if (!id || !title) throw new LifecycleError("lifecycle: id and title required");
  const { events } = read(file);
  if (stateOf(events, id) !== "unknown") return { ok: false, reason: "already-open", id };
  return { ok: true, record: append(file, { ts: now().toISOString(), id, event: "open", title, severity, by }) };
}

function transition(file, id, event, { by, note = "", now = () => new Date() }) {
  const { events } = read(file);
  const state = stateOf(events, id);
  const need = { acknowledge: "open", close: "acknowledged" }[event];
  if (state === "unknown") {
    append(file, { ts: now().toISOString(), id, event: "refused", by, note: "unknown finding" });
    return { ok: false, reason: "unknown-finding", state };
  }
  if (state !== need) {
    append(file, { ts: now().toISOString(), id, event: "refused", by, note: "needs " + need + ", is " + state });
    return { ok: false, reason: "needs-" + need, state };
  }
  return { ok: true, record: append(file, { ts: now().toISOString(), id, event, by, note }) };
}

export function acknowledgeFinding(file, id, opts = {}) {
  return transition(file, id, "acknowledge", opts);
}

export function closeFinding(file, id, opts = {}) {
  return transition(file, id, "close", opts);
}

export function chainOf(file, id) {
  const { events, torn } = read(file);
  return { id, state: stateOf(events, id), events: events.filter((e) => e.id === id), torn };
}
