// An agent that finishes its work can name the next job itself. That is the
// relay being agentic rather than a queue -- so these tests drive the real
// watchman and a real child process, and check the board it leaves behind.
import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

import { createWatchman } from "../agents/watchman.mjs";

function tmp() {
  return fs.mkdtempSync(path.join(os.tmpdir(), "meta-propose-"));
}

// The child writes its baton into its own run directory, exactly as a real
// agent does; `next` is the order it wants handed back to itself.
function writer(baton) {
  return ["node", "-e",
    "require('fs').writeFileSync('baton.json', JSON.stringify(" + JSON.stringify(baton) + "))"];
}

function board(job, command) {
  const root = tmp();
  const jobs = path.join(root, "jobs");
  fs.mkdirSync(jobs);
  const registryFile = path.join(root, "registry.json");
  fs.writeFileSync(registryFile, JSON.stringify({
    agents: [{ name: "watch", lane: "iso", command, budget: {} }],
  }));
  fs.writeFileSync(path.join(jobs, job.id + ".job.json"), JSON.stringify(job));
  return { root, jobs, watchman: createWatchman({ registryFile, root, jobsDir: jobs }) };
}

test("a clean run hands its next order back to itself", async () => {
  const { jobs, watchman } = board(
    { id: "j1", agent: "watch", orders: "sweep the first shelf" },
    writer({ stepIndex: 0, state: "first shelf clear", next: "sweep the second shelf" })
  );
  const spawned = await watchman.pollOnce();
  assert.equal(spawned.length, 1);
  await spawned[0].handle.done;
  await new Promise((resolve) => setTimeout(resolve, 60));

  const queued = watchman.ledger.read().find((entry) => entry.event === "proposal-queued");
  assert.ok(queued, "the proposal is on the ledger");
  assert.equal(queued.id, "j1");
  assert.equal(queued.next, "j1-n1");

  const next = JSON.parse(fs.readFileSync(path.join(jobs, "j1-n1.job.json"), "utf8"));
  assert.equal(next.agent, "watch", "the same agent takes its own next order");
  assert.equal(next.orders, "sweep the second shelf");
  assert.equal(next.proposedBy, queued.run, "the proposal names the run that made it");
  assert.equal(next.fromJob, "j1");
  assert.equal(next.lane, null);

  // The chain is one hop by default: the proposal may not propose again.
  assert.equal(next.proposals, 1);
  assert.equal(next.maxProposals, 1);

  // Prove the ceiling on the board, not just in the file: the proposal runs,
  // and whatever it says next, no third job appears.
  const second = await watchman.pollOnce();
  assert.equal(second.length, 1, "the proposed job is really spawned");
  await second[0].handle.done;
  await new Promise((resolve) => setTimeout(resolve, 80));
  const onBoard = fs.readdirSync(jobs).filter((name) => name.endsWith(".job.json"));
  assert.deepEqual(onBoard.sort(), ["j1-n1.job.json", "j1.job.json"]);
});

test("a job that repeats its own orders is refused, not looped", async () => {
  const { jobs, watchman } = board(
    { id: "j2", agent: "watch", orders: "sweep the shelf" },
    writer({ stepIndex: 0, next: "sweep the shelf" })
  );
  const spawned = await watchman.pollOnce();
  await spawned[0].handle.done;
  await new Promise((resolve) => setTimeout(resolve, 60));

  const refused = watchman.ledger.read().find((entry) => entry.event === "proposal-refused");
  assert.ok(refused, "the refusal is named");
  assert.equal(refused.reason, "proposal-echo");
  assert.equal(fs.existsSync(path.join(jobs, "j2-n1.job.json")), false);
});

test("a job that spent its proposal limit cannot propose", async () => {
  const { jobs, watchman } = board(
    { id: "j3", agent: "watch", orders: "one thing", proposals: 1, maxProposals: 1 },
    writer({ stepIndex: 0, next: "another thing" })
  );
  const spawned = await watchman.pollOnce();
  await spawned[0].handle.done;
  await new Promise((resolve) => setTimeout(resolve, 60));

  const refused = watchman.ledger.read().find((entry) => entry.event === "proposal-refused");
  assert.equal(refused.reason, "proposal-limit");
  assert.equal(fs.existsSync(path.join(jobs, "j3-n1.job.json")), false);
});

test("a failed run is not allowed to order more work", async () => {
  const root = tmp();
  const jobs = path.join(root, "jobs");
  fs.mkdirSync(jobs);
  const registryFile = path.join(root, "registry.json");
  fs.writeFileSync(registryFile, JSON.stringify({
    agents: [{
      name: "watch", lane: "iso", budget: {},
      command: ["node", "-e",
        "require('fs').writeFileSync('baton.json', JSON.stringify({stepIndex:0,next:'more work'})); process.exit(3)"],
    }],
  }));
  fs.writeFileSync(path.join(jobs, "j4.job.json"),
    JSON.stringify({ id: "j4", agent: "watch", orders: "do a thing" }));
  const watchman = createWatchman({ registryFile, root, jobsDir: jobs });

  const spawned = await watchman.pollOnce();
  await spawned[0].handle.done;
  await new Promise((resolve) => setTimeout(resolve, 80));

  const events = watchman.ledger.read().map((entry) => entry.event);
  assert.ok(events.includes("job-done"));
  assert.ok(events.includes("job-retry"), "the failure is retried instead");
  assert.ok(!events.includes("proposal-queued"), "a failure proposes nothing");
  assert.equal(fs.existsSync(path.join(jobs, "j4-n1.job.json")), false);
});

test("a clean run with no next order is quiet", async () => {
  const { jobs, watchman } = board(
    { id: "j5", agent: "watch", orders: "one thing" },
    writer({ stepIndex: 0, state: "done, nothing obvious next" })
  );
  const spawned = await watchman.pollOnce();
  await spawned[0].handle.done;
  await new Promise((resolve) => setTimeout(resolve, 60));

  const events = watchman.ledger.read().map((entry) => entry.event);
  assert.ok(events.includes("job-done"));
  assert.ok(!events.some((event) => event.startsWith("proposal")),
    "no baton order means no proposal, and no noise");
  assert.equal(fs.existsSync(path.join(jobs, "j5-n1.job.json")), false);
});
