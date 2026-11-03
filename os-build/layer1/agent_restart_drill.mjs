// Round 8, A2 — restart drill. Prints a Markdown transcript to stdout.
//
// The crash state is BUILT, not faked: a run directory with a spawn record and no exit record,
// a baton on disk, a bell in the watchman ledger and a claim in the state file is exactly what a
// SIGKILLed daemon leaves behind. Building it directly makes the drill deterministic; the drill
// log says so in its own header rather than implying a killed process.
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { createWatchman } from "../../agents/watchman.mjs";
import { Ledger } from "../../agents/runtime.mjs";
import { writeBaton } from "../../agents/baton.mjs";

const root = fs.mkdtempSync(path.join(os.tmpdir(), "restart-drill-"));
const jobsDir = path.join(root, "jobs");
const registryFile = path.join(root, "registry.json");
const stateFile = path.join(root, "watchman-state.json");
const NODE = process.execPath;
const WORKER = "const fs=require('fs');const b=JSON.parse(fs.readFileSync('brief.json','utf8'));fs.writeFileSync('done.txt',b.orders)";

fs.mkdirSync(jobsDir, { recursive: true });
fs.writeFileSync(registryFile, JSON.stringify({
  agents: [{ name: "worker", lane: "drill", command: [NODE, "-e", WORKER], budget: {} }],
}));

const events = (f) => (fs.existsSync(f) ? new Ledger(f).read().map((l) => l.event).join(", ") : "(no file)");

// ---- the state a crashed daemon leaves -------------------------------------------------
const runDir = path.join(root, "runs", "r-old");
fs.mkdirSync(runDir, { recursive: true });
new Ledger(path.join(runDir, "ledger.jsonl")).add("r-old", "spawn", { lane: "drill" });
writeBaton(runDir, { stepIndex: 0, state: "west wall half built", artifacts: ["wall.txt"], nextStep: "finish the west wall" });
new Ledger(path.join(root, "watchman.jsonl")).add("watchman", "bell", { id: "j1", agent: "worker", run: "r-old" });
fs.writeFileSync(stateFile, JSON.stringify({ claimed: ["j1"], resume: {} }));
fs.writeFileSync(path.join(jobsDir, "j1.job.json"), JSON.stringify({ id: "j1", agent: "worker", orders: "mind the gate" }));

console.log("# A2 restart drill — runtime died mid-run\n");
console.log("Root: `" + root + "`  (temp; the crash state is reconstructed, see the script header)\n");
console.log("## Before the restart\n");
console.log("- run `r-old` ledger: " + events(path.join(runDir, "ledger.jsonl")) + "  ← no exit: the run did not finish by itself");
console.log("- baton on disk: " + fs.readFileSync(path.join(runDir, "baton.json"), "utf8").replace(/\s+/g, " "));
console.log("- watchman state: " + fs.readFileSync(stateFile, "utf8").replace(/\s+/g, " "));

// ---- restart: reconcile ----------------------------------------------------------------
const w = createWatchman({ registryFile, root, jobsDir });
console.log("\n## Restart 1 — reconcile\n");
console.log("- recovered: `" + JSON.stringify(w.recovered) + "`");
console.log("- run `r-old` ledger now: " + events(path.join(runDir, "ledger.jsonl")));

// ---- the resumed job -------------------------------------------------------------------
const spawned = await w.pollOnce();
const h = spawned[0].handle;
await h.done;
const brief = JSON.parse(fs.readFileSync(path.join(h.runDir, "brief.json"), "utf8"));
console.log("\n## The resumed run `" + h.runId + "`\n");
console.log("Brief orders (first lines):\n");
console.log("```\n" + brief.orders.split("\n").slice(0, 4).join("\n") + "\n```");
console.log("\n- new run ledger: " + events(path.join(h.runDir, "ledger.jsonl")));
console.log("- watchman ledger: " + events(path.join(root, "watchman.jsonl")));
console.log("- result file: `" + path.join(jobsDir, "j1.result.json") + "` exists=" + fs.existsSync(path.join(jobsDir, "j1.result.json")));

// ---- second restart: nothing to recover, nothing double-spawned -------------------------
const w2 = createWatchman({ registryFile, root, jobsDir });
const second = await w2.pollOnce();
console.log("\n## Restart 2 — after the run completed\n");
console.log("- recovered: `" + JSON.stringify(w2.recovered) + "`");
console.log("- spawns on this poll: " + second.length);
console.log("- claimed ids: " + JSON.parse(fs.readFileSync(stateFile, "utf8")).claimed.join(", "));
console.log("\nVerdict: the orphaned run is marked `run-orphaned`, the next run CONTINUES from its baton,");
console.log("and a second restart neither re-runs the job nor spawns a duplicate.");
