// Round 12 baton worker — a real agent command for the handoff drill.
//
// First run: writes ONE artifact line, deposits a baton, then stays alive so the drill can kill
// the process group mid-flight. Continuation run: appends ONE line and exits. The artifact is
// append-only so duplicate work is visible as a second line, not hidden by an overwrite.
import fs from "node:fs";
import path from "node:path";
import { writeBaton } from "../../../agents/baton.mjs";

const runDir = process.cwd();
const brief = JSON.parse(fs.readFileSync(path.join(runDir, "brief.json"), "utf8"));
const artifact = path.join(runDir, "work.txt");
const continuation = /Continuation of run/.test(brief.orders || "");

if (continuation) {
  fs.appendFileSync(artifact, "continuation\n");
  fs.writeFileSync(path.join(runDir, "continued.json"), JSON.stringify({
    run: process.env.AGENT_RUN || null,
    at: new Date().toISOString(),
    orders: brief.orders,
  }, null, 2));
  writeBaton(runDir, {
    state: "west wall finished by the continuation",
    artifacts: ["work.txt", "continued.json"],
    nextStep: "none; the job is complete",
  });
  process.exit(0);
}

fs.writeFileSync(artifact, "stage-1\n");
fs.writeFileSync(path.join(runDir, "ready.txt"), "first stage done; waiting to be killed\n");
writeBaton(runDir, {
  state: "west wall half built",
  artifacts: ["work.txt"],
  nextStep: "finish the west wall; do not re-lay the first course",
});
// Alive long enough for the drill to kill the group. Never exits on its own: the proof is that
// the continuation, not this process, finished the job.
setInterval(() => {}, 1000);
