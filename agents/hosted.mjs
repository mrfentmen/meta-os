// Meta OS agent layer — hosted loops as registry entries (R11-254..261).
//
// A hosted loop is a registry entry with a real command that runs to completion and leaves a
// ledger. Two things are enforced here that the runtime alone does not:
//
//   1. A per-agent STOP file is checked BEFORE the spawn, so every loop can be stopped even if
//      its command exits faster than the runtime's 100 ms poll.
//   2. `hostedLoops()` only returns entries that are marked hosted and not marked draft, so a
//      drill cannot "pass" by spawning a placeholder `true`.
import fs from "node:fs";
import path from "node:path";
import { spawnAgent } from "./runtime.mjs";

export function stopMarker(root, name) {
  return path.join(root, "stop", name + ".STOP");
}

export function isStopped(root, name) {
  return fs.existsSync(stopMarker(root, name));
}

export function spawnHosted(agent, { root, job = {} } = {}) {
  if (!agent || agent.draft === true) {
    return { ok: false, reason: "draft-agent", detail: agent ? agent.draftReason || "marked draft" : "no agent" };
  }
  if (isStopped(root, agent.name)) {
    return { ok: false, reason: "stop-filed", detail: "stop file present before spawn" };
  }
  const handle = spawnAgent(agent, { root, job });
  return { ok: true, handle, runId: handle.runId };
}

export function hostedLoops(agents) {
  return (agents || []).filter((a) => a.hosted === true && a.draft !== true);
}

// A drill helper: the caller supplies the command that must run, so the STOP gate is proven
// against a loop that would otherwise outlive the check window.
export function stopDrill(agent, { root, job = {} } = {}) {
  fs.mkdirSync(path.join(root, "stop"), { recursive: true });
  fs.writeFileSync(stopMarker(root, agent.name), "R11-260 drill\n");
  const refused = spawnHosted(agent, { root, job });
  return { refused, cleared: () => { try { fs.unlinkSync(stopMarker(root, agent.name)); } catch { /* already gone */ } } };
}
