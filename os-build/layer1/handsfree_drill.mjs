// Round 8, C — the three Hands-Free shapes in one pass.
//
// Inbox -> watchman job files -> real runs -> one brief -> the boss's yes in a run ledger.
// Every value printed below is read back off disk or returned by the module.
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { dropOrders } from "../../handsfree/intake.mjs";
import { briefFromJobs } from "../../handsfree/brief.mjs";
import { requestApproval, dropApproval } from "../../handsfree/approval.mjs";
import { createWatchman } from "../../agents/watchman.mjs";
import { Ledger } from "../../agents/runtime.mjs";

const NODE = process.execPath;
const root = fs.mkdtempSync(path.join(os.tmpdir(), "handsfree-drill-"));
const jobsDir = path.join(root, "jobs");
const inbox = path.join(root, "inbox.txt");
const wait = (ms) => new Promise((r) => setTimeout(r, ms));

fs.writeFileSync(path.join(root, "registry.json"), JSON.stringify({
  agents: [
    { name: "worker", lane: "drill", command: [NODE, "-e", "const fs=require('fs');fs.writeFileSync('done.txt','swept')"], budget: {} },
    { name: "runner", lane: "drill", command: [NODE, "-e", "setTimeout(()=>{},30000)"], budget: { maxWallMs: 300 } },
    { name: "stopper", lane: "drill", command: [NODE, "-e", "setTimeout(()=>{},30000)"], budget: {} },
  ],
}));

const INBOX = [
  "# tonight",
  "worker: sweep the board",
  "runner: check the gate",
  "stopper: wait for the boss",
  "this line is not an order",
].join("\n") + "\n";
fs.writeFileSync(inbox, INBOX);

const intake = dropOrders(inbox, jobsDir, { now: Date.now() });

const w = createWatchman({ registryFile: path.join(root, "registry.json"), root, jobsDir });
const spawned = await w.pollOnce();
await wait(120);
// The STOP goes where the runtime polls: the run directory (window 2 of the bridge's three).
const stopper = spawned.find((s) => s.id.startsWith("stopper-"));
fs.writeFileSync(path.join(stopper.handle.runDir, "STOP"), "boss\n");
await Promise.all(spawned.map((s) => s.handle.done));

const brief = briefFromJobs(jobsDir);
const workerRun = spawned.find((s) => s.id.startsWith("worker-")).handle;
requestApproval(workerRun.runDir, { run: workerRun.runId, what: "send the sweep report", why: "announce before send" });
const approval = dropApproval(workerRun.runDir, "yes", { by: "boss" });
const approvals = new Ledger(path.join(workerRun.runDir, "ledger.jsonl")).read().filter((l) => l.event === "approval");

const out = [];
const say = (s) => out.push(s);
say("# C drill — inbox to brief, with the boss's word in the ledger\n");
say("Root: `" + root + "`\n");
say("## 1. The inbox\n");
say("```\n" + INBOX + "```");
say("- orders taken: " + intake.jobs.length + " (`" + intake.jobs.map((j) => j.id).join("`, `") + "`)");
say("- lines refused and left in the inbox: " + intake.skipped.length + " → `" + intake.skipped.map((s) => s.text).join("`, `") + "`\n");
say("## 2. The runs\n");
for (const s of spawned) say("- `" + s.id + "` → run `" + s.handle.runId + "`");
say("- STOP filed for `stopper`; `runner` has a 300 ms wall-clock budget\n");
say("## 3. The brief (speakable, verbatim)\n");
say("```\n" + brief + "```\n");
say("## 4. The approval\n");
say("- request: " + JSON.stringify(JSON.parse(fs.readFileSync(path.join(workerRun.runDir, "approval.request.json"), "utf8")).what));
say("- answer: `" + approval.decision + "` by `" + approvals[0].by + "` at `" + approvals[0].at + "`");
say("- ledger line: `" + JSON.stringify(approvals[0]) + "`");
say("\nVerdict: the inbox is text, the jobs are the watchman's own files, the brief is one block with");
say("numbers first, and the yes is in the run's append-only ledger rather than beside it.");
console.log(out.join("\n"));
