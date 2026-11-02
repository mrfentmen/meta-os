// Round 12, R12-023 + R12-024 — STOP mid-run on every hosted loop, and one budget kill.
//
// STOP: every hosted loop is spawned with a 2 ms STOP poll (the production default is 100 ms and
// is stated in the record). A STOP file is filed 5 ms after spawn. A loop that finishes before
// the poll is recorded as finished-before-stop with its duration — the pre-spawn STOP remains its
// proven path, and the report says so instead of pretending the mid-run stop happened.
//
// BUDGET: the Imperium loop is spawned with a 300 ms cap, below its real run cost. The runtime
// must write a budget receipt at the cap and kill the run; it must not raise its own budget.
import fs from "node:fs";
import path from "node:path";
import url from "node:url";
import { loadRegistry, spawnAgent, Ledger } from "../../../agents/runtime.mjs";
import { hostedLoops } from "../../../agents/hosted.mjs";

const HERE = path.dirname(url.fileURLToPath(import.meta.url));
const ROOT = path.dirname(path.dirname(path.dirname(HERE)));
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const agents = hostedLoops(loadRegistry(path.join(ROOT, "agents", "registry.json")));
// Two honest passes: EARLY puts the STOP at 5 ms for every loop (the proof that each loop can
// halt while alive); the default pass uses 40 ms for single-process loops so three of them finish
// first — a result about their speed, not a missing STOP path.
const EARLY = process.env.R12_STOP_EARLY === "1";
const stem = EARLY ? "LOOPS_DRILL_EARLY" : "LOOPS_DRILL";
const results = [];

for (const agent of agents) {
  const copy = { ...agent, stopPollMs: 2, budget: { ...(agent.budget || {}), maxWallMs: 10000 } };
  // Loops that spawn children (Imperium's queue service, the Aegis cycle's subprocesses) get a
  // 5 ms stop so the kill lands before any child exists. Single-process loops get 40 ms so the
  // stop lands after startup, not merely during it.
  const stopAfterMs = EARLY ? 5 : (agent.name === "imperium-patrol" || agent.name === "aegis-cycle" ? 5 : 40);
  const started = Date.now();
  const h = spawnAgent(copy, { root: ROOT });
  await sleep(stopAfterMs);
  const stillRunning = h.child.exitCode === null && h.child.signalCode === null;
  if (stillRunning) fs.writeFileSync(path.join(h.runDir, "STOP"), "R12-023 drill\n");
  const done = await Promise.race([h.done, sleep(9000).then(() => ({ timeout: true }))]);
  const events = new Ledger(path.join(h.runDir, "ledger.jsonl")).read();
  const stopped = events.find((e) => e.event === "stop-request");
  const exited = events.find((e) => e.event === "exit");
  results.push({
    agent: agent.name,
    command: agent.command.join(" "),
    stopFiledMidRun: stillRunning,
    stopAfterMs,
    durationMs: Date.now() - started,
    stoppedReason: stopped ? stopped.reason : null,
    exit: exited ? { code: exited.code, signal: exited.signal } : null,
    timedOut: done && done.timeout === true,
    noOrphan: h.child.exitCode !== null || h.child.signalCode !== null,
    state: stillRunning ? (stopped ? "stopped-mid-run" : "stop-filed-no-halt") : "finished-before-stop",
  });
}

// Budget kill: a real hosted loop, a cap below its startup+run cost. Nervus is used because it
// is a single process with no children, so the kill cannot orphan a service behind the parent.
const budgetAgent = agents.find((a) => a.name === "nervus");
let budget = { name: "nervus", ok: false };
if (budgetAgent) {
  const cap = 20;
  const copy = { ...budgetAgent, budget: { ...(budgetAgent.budget || {}), maxWallMs: cap } };
  const h = spawnAgent(copy, { root: ROOT });
  const done = await Promise.race([h.done, sleep(15000).then(() => ({ timeout: true }))]);
  const events = new Ledger(path.join(h.runDir, "ledger.jsonl")).read();
  const receipt = events.find((e) => e.event === "budget-receipt");
  const stopped = events.find((e) => e.event === "stop-request");
  const fileReceipt = (() => {
    try { return JSON.parse(fs.readFileSync(path.join(h.runDir, "receipt.json"), "utf8")); } catch { return null; }
  })();
  budget = {
    name: "nervus",
    capMs: cap,
    timedOut: done && done.timeout === true,
    stoppedReason: stopped ? stopped.reason : null,
    receipt: receipt || null,
    fileReceipt,
    ok: !!(receipt && receipt.reason === "budget-wall-clock" && receipt.capMs === cap &&
      fileReceipt && fileReceipt.capMs === cap && stopped && stopped.reason === "budget-wall-clock"),
    registryBudgetUnchanged: budgetAgent.budget.maxWallMs,
  };
}

const stoppedCount = results.filter((r) => r.state === "stopped-mid-run").length;
const finishedCount = results.filter((r) => r.state === "finished-before-stop").length;
const ok = results.every((r) => r.noOrphan && r.state !== "stop-filed-no-halt" && !r.timedOut) && budget.ok;
const receipt = {
  tasks: ["R12-023", "R12-024"],
  at: new Date().toISOString(),
  ok,
  pass: EARLY ? "early" : "late",
  pollMs: 2,
  productionPollMs: 100,
  loops: results,
  summary: { loops: results.length, stoppedMidRun: stoppedCount, finishedBeforeStop: finishedCount },
  budget,
  note: "STOP poll accelerated to 2 ms for the drill; loops that finish in a few ms cannot be " +
    "halted mid-run under the production 100 ms poll, and their pre-spawn STOP is the proven path. " +
    "Budget cap is below the real run cost; the runtime receipt records the cap it enforced.",
};
fs.writeFileSync(path.join(HERE, stem + ".json"), JSON.stringify(receipt, null, 2) + "\n");
const md = [
  "# Hosted loop drills — R12-023 (STOP) and R12-024 (budget)",
  "",
  "Pass: **" + (EARLY ? "early STOP at 5 ms for every loop" : "late STOP at 40 ms for single-process loops") + "**.",
  "",
  "Run at " + receipt.at + ". **" + (ok ? "PASS" : "FAIL") + "**",
  "",
  "STOP poll was **2 ms** for this drill (production default **100 ms**, stated because it changes",
  "what the fast loops can prove).",
  "",
  "| loop | stop filed mid-run | outcome | stopped reason | exit | duration | no orphan |",
  "|---|---|---|---|---|---|---|",
];
for (const r of results) {
  md.push("| `" + r.agent + "` | " + r.stopFiledMidRun + " | **" + r.state + "** | " +
    (r.stoppedReason || "—") + " | " + (r.exit ? r.exit.code + "/" + (r.exit.signal || "null") : "—") +
    " | " + r.durationMs + " ms | " + r.noOrphan + " |");
}
md.push("");
md.push("Budget drill: `nervus` capped at **" + budget.capMs + " ms** against a real run");
md.push("that costs longer. Runtime receipt: " + (budget.receipt ? "`" + budget.receipt.reason + "` cap " + budget.receipt.capMs : "**missing**") +
  "; registry cap unchanged at " + budget.registryBudgetUnchanged + " ms. **" + (budget.ok ? "PASS" : "FAIL") + "**");
md.push("");
md.push("## What this does not claim");
md.push("");
md.push("- A loop that finished before the STOP landed did not halt mid-run. Those rows say");
md.push("  `finished-before-stop`; their guaranteed path is the pre-spawn STOP (`tests/r12-loops`).");
md.push("- No kernel, no supervisor, no signal delivered by anything but the host runtime.");
fs.writeFileSync(path.join(HERE, stem + ".md"), md.join("\n") + "\n");
console.log("loop drills: " + (ok ? "PASS" : "FAIL") + " stopped=" + stoppedCount + " finished=" + finishedCount +
  " budget=" + budget.ok);
process.exit(ok ? 0 : 1);
