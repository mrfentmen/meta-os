// Round 12, R12-038/039 — Hands-Free through Cadence, and the three intake refusals.
//
// R12-038 runs one typed order all the way through the real pieces: dropOrders writes the job,
// the real watchman claims and spawns it, the agent process exits, the watchman writes the
// result, and briefFromJobs composes the brief. The latency is measured around that path and
// written to a receipt under os-build/layer1/r12/. Nothing here is a simulated agent: the
// registry entry is a real child process with a real exit code.
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { createWatchman } from "../agents/watchman.mjs";
import { dropOrders, parseInbox, MAX_ORDER_CHARS } from "../handsfree/intake.mjs";
import { briefFromJobs } from "../handsfree/brief.mjs";

const tmp = () => fs.mkdtempSync(path.join(os.tmpdir(), "hf-cadence-"));

function waitForFile(file, timeoutMs = 4000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    if (fs.existsSync(file)) return true;
    // The test runner is single-threaded but the child is not; a short sleep yields to its exit.
    Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 10);
  }
  return false;
}

test("R12-038 one typed order becomes a watchman run and a brief, with latency recorded", async () => {
  const root = tmp();
  const jobsDir = path.join(root, "jobs");
  const inbox = path.join(root, "inbox.txt");
  fs.mkdirSync(jobsDir, { recursive: true });
  fs.writeFileSync(inbox, "worker: stage the board for the night pass\n");

  const registryFile = path.join(root, "registry.json");
  fs.writeFileSync(registryFile, JSON.stringify({
    agents: [{
      name: "worker",
      command: [process.execPath, "-e", "process.exit(0)"],
      budget: { maxWallMs: 5000 },
    }],
  }));

  const filed = dropOrders(inbox, jobsDir, { now: 1_700_000_000_000 });
  assert.equal(filed.jobs.length, 1);
  assert.equal(filed.refusals.length, 0);
  const jobFile = path.join(jobsDir, filed.jobs[0].id + ".job.json");
  const job = JSON.parse(fs.readFileSync(jobFile, "utf8"));
  assert.equal(job.agent, "worker");
  assert.match(job.orders, /stage the board/);

  const started = process.hrtime.bigint();
  const watchman = createWatchman({
    registryFile,
    root,
    jobsDir,
    heartbeatFile: path.join(root, "watchman.heartbeat.json"),
  });
  const spawned = await watchman.pollOnce();
  assert.equal(spawned.length, 1, "the real watchman claimed exactly one job");
  await spawned[0].handle.done;

  const resultFile = path.join(jobsDir, job.id + ".result.json");
  assert.ok(waitForFile(resultFile), "the watchman wrote a result for the run");
  const result = JSON.parse(fs.readFileSync(resultFile, "utf8"));
  assert.equal(result.code, 0);
  assert.equal(result.signal, null);

  const brief = briefFromJobs(jobsDir);
  const latencyMs = Number((process.hrtime.bigint() - started) / 1_000_000n);
  assert.equal(brief, "1 order ran.\n1 finished, 0 stopped, 0 failed.\nworker finished.\n");

  const receiptDir = path.resolve(import.meta.dirname, "..", "os-build", "layer1", "r12");
  fs.mkdirSync(receiptDir, { recursive: true });
  fs.writeFileSync(path.join(receiptDir, "HANDSFREE_CADENCE.json"), JSON.stringify({
    task: "R12-038",
    ranAt: new Date().toISOString(),
    path: ["inbox line", "dropOrders job file", "watchman claim+spawn", "agent exit 0", "result file", "briefFromJobs"],
    inboxOrders: 1,
    jobsFiled: filed.jobs.length,
    runsSpawned: spawned.length,
    resultCode: result.code,
    brief,
    latencyMs,
    note: "Host process, real child exit. No kernel, no voice, no model.",
  }, null, 2) + "\n");
});

test("R12-039 malformed intake is refused, recorded, and left in the inbox", () => {
  const dir = tmp();
  const inbox = path.join(dir, "inbox.txt");
  const jobsDir = path.join(dir, "jobs");
  fs.writeFileSync(inbox, "this line has no owner\n");
  const r = dropOrders(inbox, jobsDir, { now: 1_700_000_000_000 });
  assert.equal(r.jobs.length, 0);
  assert.equal(r.skipped.length, 1);
  assert.match(r.skipped[0].reason, /no agent before a colon/);
  assert.equal(fs.readFileSync(inbox, "utf8"), "this line has no owner\n", "the bad line is not deleted");
  const records = fs.readFileSync(inbox + ".refusals.jsonl", "utf8").trim().split("\n").map((l) => JSON.parse(l));
  assert.equal(records.length, 1);
  assert.equal(records[0].event, "refused");
  assert.equal(records[0].line, 1);
  assert.match(records[0].text_hash, /^[0-9a-f]{16}$/);
  assert.equal(records[0].text, undefined, "the refusal record does not copy the order text");
});

test("R12-039 an empty inbox is a recorded refusal, not a silent success", () => {
  const dir = tmp();
  const inbox = path.join(dir, "inbox.txt");
  const jobsDir = path.join(dir, "jobs");
  fs.writeFileSync(inbox, "", "utf8");
  const r = dropOrders(inbox, jobsDir, { now: 1_700_000_000_000 });
  assert.equal(r.jobs.length, 0);
  assert.equal(r.refusals.length, 1);
  const rec = JSON.parse(fs.readFileSync(inbox + ".refusals.jsonl", "utf8").trim());
  assert.equal(rec.reason, "empty-inbox");
  assert.equal(rec.at, new Date(1_700_000_000_000).toISOString());
});

test("R12-039 an oversized order is refused with its length, not truncated or run", () => {
  const dir = tmp();
  const inbox = path.join(dir, "inbox.txt");
  const jobsDir = path.join(dir, "jobs");
  const line = "worker: " + "x".repeat(MAX_ORDER_CHARS);
  fs.writeFileSync(inbox, line + "\n");
  const r = dropOrders(inbox, jobsDir, { now: 1_700_000_000_000 });
  assert.equal(r.jobs.length, 0);
  assert.equal(r.skipped[0].reason, "oversized-order");
  assert.equal(r.skipped[0].length, line.length);
  assert.equal(fs.readFileSync(inbox, "utf8"), line + "\n");
  const rec = JSON.parse(fs.readFileSync(inbox + ".refusals.jsonl", "utf8").trim());
  assert.equal(rec.reason, "oversized-order");
  assert.equal(rec.length, line.length);
});

test("R12-039 parseInbox still accepts a normal order after the new limits", () => {
  const { jobs, skipped } = parseInbox("worker: one\nrunner: two\n");
  assert.deepEqual(jobs, [{ agent: "worker", orders: "one" }, { agent: "runner", orders: "two" }]);
  assert.deepEqual(skipped, []);
});
