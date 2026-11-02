// Round 12, R12-021 — Imperium baton pass.
//
// The real hosted queue-stack pass is started, killed by SIGKILL to its process group after its
// baton exists, then resumed with `--resume` against the same run directory. The proof is the
// dispatch log: exactly one simulated package in the whole run directory. A resume that re-POSTed
// would show two.
import fs from "node:fs";
import path from "node:path";
import { spawn } from "node:child_process";
import url from "node:url";

const HERE = path.dirname(url.fileURLToPath(import.meta.url));
const ROOT = path.dirname(path.dirname(path.dirname(HERE)));
const work = path.join(HERE, "imperium-baton");
fs.rmSync(work, { recursive: true, force: true });
fs.mkdirSync(work, { recursive: true });
const script = path.join(ROOT, "server", "queue", "hosted_imperium.py");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function start(resume) {
  const args = [script, "--run-dir", work];
  if (resume) args.push("--resume");
  const child = spawn("python3", args, { cwd: ROOT, detached: true, stdio: ["ignore", "pipe", "pipe"] });
  let out = "";
  child.stdout.on("data", (d) => { out += d; });
  child.stderr.on("data", (d) => { out += d; });
  return { child, output: () => out };
}

async function waitFor(pred, ms, label) {
  const startAt = Date.now();
  while (Date.now() - startAt < ms) {
    if (pred()) return Date.now() - startAt;
    await sleep(15);
  }
  throw new Error("timed out waiting for " + label);
}

const first = start(false);
const batonFile = path.join(work, "baton.json");
await waitFor(() => fs.existsSync(batonFile), 30000, "first baton");
const batonAtKill = JSON.parse(fs.readFileSync(batonFile, "utf8"));
// Kill before the pass finishes if it is still alive; if it already exited, the resume still has
// to prove it does not dispatch twice, and the receipt records which case happened.
let killed = false;
try { process.kill(-first.child.pid, "SIGKILL"); killed = true; } catch { /* already exited */ }
await sleep(200);

const restartAt = Date.now();
const second = start(true);
const exit = await new Promise((resolve) => second.child.on("close", (code, signal) => resolve({ code, signal })));
const resumedMs = Date.now() - restartAt;
const output = second.output();

const receiptFile = path.join(work, "receipt.json");
const receipt = fs.existsSync(receiptFile) ? JSON.parse(fs.readFileSync(receiptFile, "utf8")) : null;
const logFile = path.join(work, "dispatch-log.jsonl");
const dispatchLines = fs.existsSync(logFile)
  ? fs.readFileSync(logFile, "utf8").trim().split("\n").filter(Boolean).map((l) => JSON.parse(l))
  : [];
const ok = exit.code === 0 && receipt && receipt.ok === true &&
  dispatchLines.length === 1 && receipt.dispatchesInRunDir === 1 &&
  (receipt.stages.dispatch.state === "accepted" || receipt.stages.dispatch.state === "skipped");

const evidence = {
  task: "R12-021",
  at: new Date().toISOString(),
  ok,
  killedMidRun: killed,
  batonAtKill,
  resume: { exit: exit.code, signal: exit.signal, ms: resumedMs },
  dispatchesInRunDir: dispatchLines.length,
  receipt: receipt && {
    ok: receipt.ok,
    resumed: receipt.resumed,
    stages: receipt.stages,
    runDir: receipt.runDir,
  },
  outputTail: output.trim().split("\n").slice(-8),
  note: "real queue service, real resident agent, real /dispatch-simulated; killed by process group",
};
fs.writeFileSync(path.join(HERE, "IMPERIUM_BATON.json"), JSON.stringify(evidence, null, 2) + "\n");
fs.writeFileSync(path.join(HERE, "IMPERIUM_BATON.md"), [
  "# Imperium baton pass — R12-021",
  "",
  "Run at " + evidence.at + ". **" + (ok ? "PASS" : "FAIL") + "**",
  "",
  "| item | value |",
  "|---|---|",
  "| killed mid-run | " + killed + " |",
  "| baton at kill | " + (batonAtKill.state || "") + "; done: " + ((batonAtKill.done || []).join(", ") || "(none)") + " |",
  "| resume exit | " + exit.code + " in " + resumedMs + " ms |",
  "| dispatches in run dir | **" + dispatchLines.length + "** |",
  "| final stages | queue " + (receipt ? receipt.stages.queue_service.state : "?") +
    ", agent " + (receipt ? receipt.stages.agent_once.state : "?") +
    ", dispatch " + (receipt ? receipt.stages.dispatch.state : "?") + " |",
  "",
  "One dispatch-log line means the continuation did not re-send the package. The SQLite store and",
  "the baton live inside the same run directory, so the resumed pass reads the work it already",
  "did instead of starting over.",
  "",
  "## Limits",
  "",
  "- Simulated loopback dispatch only; no real service contacted.",
  "- No model call, no assessment.",
  "",
].join("\n"));

console.log("imperium baton: " + (ok ? "PASS" : "FAIL") +
  " killed=" + killed + " dispatchLines=" + dispatchLines.length + " resumeExit=" + exit.code + " ms=" + resumedMs);
process.exit(ok ? 0 : 1);
