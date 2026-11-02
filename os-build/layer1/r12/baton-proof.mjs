// Round 12, R12-022 + R12-025 — Cadence baton pass and watchman death drill.
//
// Real processes, real kill:
//   1. a watchman daemon claims a job and spawns the baton worker;
//   2. the worker writes one artifact line and deposits a baton;
//   3. the drill SIGKILLs the whole process group (watchman AND worker) — no clean exit;
//   4. a fresh watchman reconciles: the run has no exit, so it is marked run-orphaned and the
//      job is re-queued to continue from that run;
//   5. the continuation appends ONE line and finishes.
//
// The proof is the artifact: "stage-1" appears once, "continuation" appears once. A restart that
// re-laid the first course would show two stage-1 lines.
import fs from "node:fs";
import path from "node:path";
import { spawn } from "node:child_process";
import url from "node:url";
import { readBeat, checkBeat } from "../../../agents/watchdog.mjs";

const HERE = path.dirname(url.fileURLToPath(import.meta.url));
const ROOT = path.dirname(path.dirname(path.dirname(HERE)));
const work = path.join(HERE, "baton-drill");
fs.rmSync(work, { recursive: true, force: true });
fs.mkdirSync(work, { recursive: true });
const jobsDir = path.join(work, "jobs");
fs.mkdirSync(jobsDir, { recursive: true });

const registryFile = path.join(work, "registry.json");
fs.writeFileSync(registryFile, JSON.stringify({
  agents: [{
    name: "worker",
    lane: "baton drill",
    command: [process.execPath, path.join(HERE, "baton-worker.mjs")],
    budget: { maxWallMs: 60000 },
  }],
}));

const job = { id: "baton-1", agent: "worker", orders: "build the west wall" };
fs.writeFileSync(path.join(jobsDir, "baton-1.job.json"), JSON.stringify(job));

const heartbeat = path.join(work, "watchman.heartbeat.json");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
async function waitFor(pred, ms = 8000, label = "condition") {
  const start = Date.now();
  while (Date.now() - start < ms) {
    if (pred()) return Date.now() - start;
    await sleep(20);
  }
  throw new Error("timed out waiting for " + label);
}
function startDaemon() {
  return spawn(process.execPath, [path.join(HERE, "watchman-daemon.mjs"), work, registryFile, jobsDir], {
    cwd: ROOT, detached: true, stdio: ["ignore", "pipe", "pipe"],
  });
}

const first = startDaemon();
let firstOut = "";
first.stdout.on("data", (d) => { firstOut += d; });
first.stderr.on("data", (d) => { firstOut += d; });

const findRunFile = (name) => {
  const dir = path.join(work, "runs");
  if (!fs.existsSync(dir)) return null;
  for (const d of fs.readdirSync(dir)) {
    const f = path.join(dir, d, name);
    if (fs.existsSync(f)) return { run: d, file: f };
  }
  return null;
};
await waitFor(() => fs.existsSync(path.join(work, "watchman.pid")), 8000, "watchman pid");
// ready.txt and baton.json live in the RUN directory (the worker's cwd), not the drill root.
await waitFor(() => findRunFile("ready.txt") && findRunFile("baton.json"), 8000, "worker baton");
const firstRun = findRunFile("ready.txt").run;
const killedAt = Date.now();
process.kill(-first.pid, "SIGKILL");   // whole group: daemon + worker, no cleanup
await sleep(250);
// The first watchman may have written a result in the exit event before the kill landed. Record
// it: a result with a signal is exactly the state the restart must NOT treat as finished.
let killedResult = null;
try { killedResult = JSON.parse(fs.readFileSync(path.join(jobsDir, "baton-1.result.json"), "utf8")); } catch {}

const beatBeforeRestart = readBeat(heartbeat, Date.now());
const beatFresh = beatBeforeRestart.beat !== null && beatBeforeRestart.ageMs <= 150;
const alarm = checkBeat(heartbeat, { maxAgeMs: 150, now: Date.now(), stateFile: path.join(work, "watchman.alarm.json") });

const restartAt = Date.now();
const second = startDaemon();
let secondOut = "";
second.stdout.on("data", (d) => { secondOut += d; });
second.stderr.on("data", (d) => { secondOut += d; });

const resultFile = path.join(jobsDir, "baton-1.result.json");
let restarted;
try {
  restarted = await waitFor(() => fs.existsSync(resultFile), 15000, "result after restart");
} catch (err) {
  console.error("first daemon output:\n" + firstOut);
  console.error("second daemon output:\n" + secondOut);
  throw err;
}
const result = JSON.parse(fs.readFileSync(resultFile, "utf8"));
// The result is written by the exit callback; give the watchman's own ledger a moment to flush
// before reading it, then read the artifact across BOTH runs. The first run owns stage-1 and the
// continuation run owns the continuation line; looking only at the first run's file read 0.
await sleep(150);
const runDirs = fs.readdirSync(path.join(work, "runs"));
const lines = runDirs.flatMap((d) => {
  const f = path.join(work, "runs", d, "work.txt");
  return fs.existsSync(f) ? fs.readFileSync(f, "utf8").trim().split("\n").filter(Boolean) : [];
});
const ledgers = runDirs.map((d) => {
  const f = path.join(work, "runs", d, "ledger.jsonl");
  return fs.existsSync(f) ? fs.readFileSync(f, "utf8").trim().split("\n").filter(Boolean).map(JSON.parse) : [];
});
const watchmanEvents = (() => {
  const f = path.join(work, "watchman.jsonl");
  return fs.existsSync(f) ? fs.readFileSync(f, "utf8").trim().split("\n").filter(Boolean).map(JSON.parse) : [];
})();
const events = [...ledgers.flat(), ...watchmanEvents];
const orphaned = events.filter((e) => e.event === "run-orphaned");
const batonPass = events.filter((e) => e.event === "baton-pass");
const stageOne = lines.filter((l) => l === "stage-1").length;
const continuation = lines.filter((l) => l === "continuation").length;

const ok = result.code === 0 && stageOne === 1 && continuation === 1 &&
  orphaned.length === 1 && batonPass.length === 1 && alarm.state === "dead" && !beatFresh &&
  (killedResult === null || killedResult.signal != null);
const receipt = {
  task: "R12-022 + R12-025",
  at: new Date().toISOString(),
  ok,
  killedProcessGroup: first.pid,
  firstRun,
  result: { code: result.code, signal: result.signal, run: result.run },
  killedRunResult: killedResult,
  artifacts: { lines, stageOne, continuation },
  recovery: {
    orphanedRecords: orphaned.length,
    batonPassRecords: batonPass.length,
    heartbeatBeforeRestart: { ageMs: beatBeforeRestart.ageMs, fresh: beatFresh },
    alarm: { state: alarm.state, line: alarm.alarm },
    restartToResultMs: restarted,
  },
  daemons: { firstOutputTail: firstOut.trim().split("\n").slice(-3), secondOutputTail: secondOut.trim().split("\n").slice(-3) },
  note: "SIGKILL to the process group; the continuation is a separate run composed from the baton. " +
    "No duplicate artifact line. Host processes only.",
};
fs.writeFileSync(path.join(HERE, "BATON_PROOF.json"), JSON.stringify(receipt, null, 2) + "\n");
const md = [
  "# Cadence baton pass and watchman death — R12-022 / R12-025",
  "",
  "Run at " + receipt.at + ". **" + (ok ? "PASS" : "FAIL") + "**",
  "",
  "| item | value |",
  "|---|---|",
  "| first run | `" + firstRun + "` |",
  "| kill | SIGKILL to process group " + first.pid + " (watchman + worker) |",
  "| heartbeat age at check | " + beatBeforeRestart.ageMs + " ms, fresh=" + beatFresh + " |",
  "| alarm raised | **" + alarm.state + "** — " + (alarm.alarm || "(none)") + " |",
  "| orphan records | " + orphaned.length + " |",
  "| baton-pass records | " + batonPass.length + " |",
  "| restart to result | " + restarted + " ms |",
  "| `stage-1` lines | " + stageOne + " |",
  "| `continuation` lines | " + continuation + " |",
  "| final exit | " + result.code + " |",
  "",
  "Across the two runs the artifact has one stage-1 line and one continuation line: the handoff",
  "continued the work, it did not redo it. The dead run is marked `run-orphaned`; the new run is",
  "a different id.",
  "",
  "## Limits",
  "",
  "- Host processes, not the kernel. No scheduler, no address space.",
  "- The alarm is `agents/watchdog.mjs` on a 150 ms threshold; the production default is larger.",
  "- Only the Cadence loop is exercised here. Imperium's proof is `IMPERIUM_BATON.json`.",
  "",
].join("\n");
fs.writeFileSync(path.join(HERE, "BATON_PROOF.md"), md);
second.kill("SIGTERM");
console.log("baton/watchman drill: " + (ok ? "PASS" : "FAIL") +
  " stage1=" + stageOne + " continuation=" + continuation +
  " orphaned=" + orphaned.length + " restartMs=" + restarted + " alarm=" + alarm.alarm);
process.exit(ok ? 0 : 1);
