// Hands-Free C8 — a session record another agent can replay (R11-248).
//
// The record holds the inputs, not only the output: the orders that were filed, the approval
// answers, the results, and the brief that was spoken. `replay` recomposes the brief from those
// results. If the recomposed text differs from the recorded one, the record is not replayable
// and says so — it does not silently "reconstruct" something else.
import fs from "node:fs";
import { composeBrief } from "./brief.mjs";
import { writeFileLoud } from "../agents/safe-write.mjs";

export function buildSession({ id, orders = [], results = [], approvals = [], brief = null, now = () => new Date() }) {
  if (!id) throw new Error("session: id required");
  const spoken = brief == null ? composeBrief(results) : brief;
  return {
    v: 1,
    id,
    at: now().toISOString(),
    orders,
    results,
    approvals,
    brief: spoken,
    replayable: true,
  };
}

export function writeSession(file, session) {
  writeFileLoud(file, JSON.stringify(session, null, 2));
  return session;
}

export function replay(session) {
  if (!session || !Array.isArray(session.results)) {
    return { ok: false, reason: "no-results-in-record", brief: null, matches: false };
  }
  const brief = composeBrief(session.results);
  return {
    ok: brief === session.brief,
    reason: brief === session.brief ? "matches" : "brief-does-not-recompose",
    brief,
    matches: brief === session.brief,
    recorded: session.brief,
  };
}

export function readSession(file) {
  return JSON.parse(fs.readFileSync(file, "utf8"));
}
