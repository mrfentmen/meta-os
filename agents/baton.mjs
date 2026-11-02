// The baton pass (OS-125, the boss's refinement): workers deposit
// progress into the job record AS THEY GO; on reassignment the
// watchman composes a continuation brief from that record.
// Continuation, never restart.
import fs from "node:fs";
import path from "node:path";

export function writeBaton(runDir, baton) {
  // CB-005: a finished job has nothing to continue. Refuse the handoff and
  // leave the reason on disk instead of overwriting the baton with a lie.
  if (baton && baton.finished === true) {
    const refusal = { refused: "baton", reason: "job already finished", ts: new Date().toISOString() };
    try { fs.writeFileSync(path.join(runDir, "baton-refused.json"), JSON.stringify(refusal, null, 2)); } catch { /* refusal still thrown */ }
    throw new Error("baton refused: job already finished");
  }
  const full = { state: "", artifacts: [], nextStep: "", ...baton, ts: new Date().toISOString() };
  fs.writeFileSync(path.join(runDir, "baton.json"), JSON.stringify(full, null, 2));
  return full;
}

export function readBaton(runDir) {
  try { return JSON.parse(fs.readFileSync(path.join(runDir, "baton.json"), "utf8")); }
  catch { return null; }
}

// CB-006: a handoff chain keeps ONE job id and records each author in order.
// A changed job id is a new job, not a continuation, so it is refused.
export function handoffChain(links) {
  if (!Array.isArray(links) || links.length === 0) {
    throw new Error("baton chain: at least one link is required");
  }
  const jobId = links[0].jobId;
  if (!jobId) throw new Error("baton chain: link 0 missing jobId");
  const authors = [];
  for (let i = 0; i < links.length; i++) {
    if (links[i].jobId !== jobId) {
      throw new Error("baton chain: job id changed at link " + i);
    }
    if (!links[i].author) {
      throw new Error("baton chain: missing author at link " + i);
    }
    authors.push(links[i].author);
  }
  return { jobId, authors };
}

export function continuationOrders(fromRun, baton, extra = "") {
  return [
    "Continuation of run " + fromRun + " — pick up the baton, do not restart.",
    "State: " + (baton.state || "(none recorded)"),
    "Artifacts so far: " + (baton.artifacts && baton.artifacts.length ? baton.artifacts.join(", ") : "(none)"),
    "Next step: " + (baton.nextStep || "(none recorded)"),
    extra,
  ].filter(Boolean).join("\n");
}
