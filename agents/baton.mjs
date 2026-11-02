// The baton pass (OS-125, the boss's refinement): workers deposit
// progress into the job record AS THEY GO; on reassignment the
// watchman composes a continuation brief from that record.
// Continuation, never restart.
import fs from "node:fs";
import path from "node:path";

export function writeBaton(runDir, baton) {
  const full = { state: "", artifacts: [], nextStep: "", ...baton, ts: new Date().toISOString() };
  fs.writeFileSync(path.join(runDir, "baton.json"), JSON.stringify(full, null, 2));
  return full;
}

export function readBaton(runDir) {
  try { return JSON.parse(fs.readFileSync(path.join(runDir, "baton.json"), "utf8")); }
  catch { return null; }
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
