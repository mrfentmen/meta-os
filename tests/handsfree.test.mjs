// Round 8, C1-C3 — Hands-Free: intake, brief, approval.
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { parseInbox, dropOrders } from "../handsfree/intake.mjs";
import { composeBrief, briefFromJobs } from "../handsfree/brief.mjs";
import { requestApproval, dropApproval, readApproval, mayAct } from "../handsfree/approval.mjs";

const tmp = () => fs.mkdtempSync(path.join(os.tmpdir(), "handsfree-"));

test("C1.1 the inbox parses lines, ignores comments, and refuses what it cannot read", () => {
  const { jobs, skipped } = parseInbox([
    "# orders for tonight",
    "worker: sweep the board",
    "",
    "runner:   check the gate  ",
    "this line has no agent",
    "pax:",
  ].join("\n"));
  assert.deepEqual(jobs, [
    { agent: "worker", orders: "sweep the board" },
    { agent: "runner", orders: "check the gate" },
  ]);
  assert.equal(skipped.length, 2);
  assert.equal(skipped[0].line, 5);
  assert.match(skipped[1].reason, /empty/);
});

test("C1.2 an order becomes a job file, and a malformed line stays in the inbox", () => {
  const dir = tmp();
  const inbox = path.join(dir, "inbox.txt");
  const jobsDir = path.join(dir, "jobs");
  fs.writeFileSync(inbox, "worker: one\nbad line\nrunner: two\n");
  const r = dropOrders(inbox, jobsDir, { now: 1_700_000_000_000 });
  assert.equal(r.jobs.length, 2);
  assert.equal(r.skipped.length, 1);
  // Files are named by id, and ids start with the agent, so a directory sort puts "runner"
  // first. Find the job by its agent instead of by position.
  const files = fs.readdirSync(jobsDir).filter((f) => f.endsWith(".job.json"));
  assert.equal(files.length, 2);
  const jobs = files.map((f) => JSON.parse(fs.readFileSync(path.join(jobsDir, f), "utf8")));
  const workerJob = jobs.find((j) => j.agent === "worker");
  assert.equal(workerJob.orders, "one");
  assert.equal(fs.readFileSync(inbox, "utf8"), "bad line\n", "only the unreadable line is left");
  assert.match(fs.readFileSync(inbox + ".done", "utf8"), /worker/);
  // Re-running the now-empty inbox writes nothing new.
  assert.equal(dropOrders(inbox, jobsDir, { now: 1_700_000_001_000 }).jobs.length, 0);
});

test("C2.1 the brief is numbers first, one plain sentence per run", () => {
  const brief = composeBrief([
    { id: "a1", agent: "worker", code: 0 },
    { id: "b2", agent: "runner", code: null, signal: "SIGTERM" },
    { id: "c3", agent: "crashy", code: 3 },
  ]);
  assert.equal(brief, [
    "3 orders ran.",
    "1 finished, 1 stopped, 1 failed.",
    "worker finished.",
    "runner was stopped.",
    "crashy failed (code 3).",
    "",
  ].join("\n"));
});

test("C2.2 the brief handles zero and one without saying '1 orders'", () => {
  assert.equal(composeBrief([]), "No orders ran.\n");
  assert.equal(composeBrief([{ id: "a", agent: "worker", code: 0 }]),
    "1 order ran.\n1 finished, 0 stopped, 0 failed.\nworker finished.\n");
});

test("C2.3 the brief reads real result files and skips a torn one", () => {
  const dir = tmp();
  const jobsDir = path.join(dir, "jobs");
  fs.mkdirSync(jobsDir, { recursive: true });
  fs.writeFileSync(path.join(jobsDir, "a.result.json"), JSON.stringify({ id: "a", agent: "worker", code: 0 }));
  fs.writeFileSync(path.join(jobsDir, "b.result.json"), '{"id":"b","agent":');
  assert.equal(briefFromJobs(jobsDir), "1 order ran.\n1 finished, 0 stopped, 0 failed.\nworker finished.\n");
});

test("C3.1 nothing acts before the boss's word", () => {
  const dir = tmp();
  assert.equal(readApproval(dir).state, "none");
  assert.equal(mayAct(dir), false);
  assert.equal(dropApproval(dir, "yes").reason, "no-request");

  const r = requestApproval(dir, { run: "run-1", what: "send the nightly report", now: 1000 });
  assert.ok(r.ok);
  assert.equal(readApproval(dir).state, "pending");
  assert.equal(mayAct(dir), false);
  assert.equal(requestApproval(dir, { run: "run-1", what: "again" }).reason, "already-pending");
});

test("C3.2 a yes lands in the run ledger, timestamped, once", () => {
  const dir = tmp();
  requestApproval(dir, { run: "run-1", what: "send the nightly report", now: 1000 });
  const yes = dropApproval(dir, "YES", { by: "boss", now: 2000 });
  assert.ok(yes.ok);
  assert.equal(readApproval(dir).state, "allowed");
  assert.equal(mayAct(dir), true);

  const ledger = fs.readFileSync(path.join(dir, "ledger.jsonl"), "utf8").trim().split("\n").map((l) => JSON.parse(l));
  assert.equal(ledger.length, 1);
  assert.equal(ledger[0].event, "approval");
  assert.equal(ledger[0].decision, "yes");
  assert.equal(ledger[0].by, "boss");
  assert.equal(ledger[0].at, "1970-01-01T00:00:02.000Z");
  assert.equal(ledger[0].what, "send the nightly report");

  // A second, conflicting answer is refused and does not change the decision. It IS logged as a
  // duplicate (R11-243): hearing an approval twice is a fact the record must keep, while the
  // approval itself still counts once.
  const dup = dropApproval(dir, "no");
  assert.equal(dup.reason, "already-answered");
  assert.equal(dup.duplicate, true);
  assert.equal(readApproval(dir).state, "allowed");
  const events = fs.readFileSync(path.join(dir, "ledger.jsonl"), "utf8").trim().split("\n").map((l) => JSON.parse(l));
  assert.deepEqual(events.map((e) => e.event), ["approval", "approval-duplicate"]);
  assert.equal(events[0].decision, "yes");
  assert.ok(fs.readFileSync(path.join(dir, "approval-duplicates.jsonl"), "utf8").includes("no"));
});

test("C3.3 a no denies, a shrug is refused, and the difference is in the record", () => {
  const dir = tmp();
  requestApproval(dir, { run: "run-2", what: "delete the old images", now: 1000 });
  assert.equal(dropApproval(dir, "maybe").reason, "bad-answer");
  assert.equal(readApproval(dir).state, "pending");
  const no = dropApproval(dir, "n", { by: "boss", now: 3000 });
  assert.ok(no.ok);
  assert.equal(readApproval(dir).state, "denied");
  assert.equal(mayAct(dir), false);
  const line = JSON.parse(fs.readFileSync(path.join(dir, "ledger.jsonl"), "utf8").trim());
  assert.equal(line.decision, "no");
});
