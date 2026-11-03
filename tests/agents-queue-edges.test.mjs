// CB2-395: FIFO order for queued jobs.
//
// `agents/queue.mjs` is a package contract (id, agent, picture) and holds no
// order, so there is nothing there to dequeue. The job queue the crew actually
// drains is `agents/room1.mjs`; that is where order is real, and that is what
// this file pins: three posted jobs drain oldest id first, once each, and a
// second drain finds nothing.
import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { drainOnce, listJobs, postJob } from "../agents/room1.mjs";

function room() {
  return mkdtempSync(join(tmpdir(), "agents-queue-"));
}

test("three queued jobs dequeue in FIFO order, once each", async () => {
  const dir = room();
  try {
    for (const id of ["j1", "j2", "j3"]) {
      postJob(dir, { id, agent: "worker", orders: "order for " + id });
    }
    assert.deepEqual(listJobs(dir).unclaimed, ["j1", "j2", "j3"]);

    const seen = [];
    const drained = await drainOnce(dir, {
      owner: "relay-a",
      handle: async (job) => {
        seen.push(job.id);
        return { orders: job.orders };
      },
    });

    assert.deepEqual(seen, ["j1", "j2", "j3"], "oldest id first");
    assert.deepEqual(
      drained.map((entry) => entry.id),
      ["j1", "j2", "j3"]
    );
    assert.equal(
      drained.every((entry) => entry.claimed && entry.ok),
      true
    );
    assert.deepEqual(listJobs(dir).unclaimed, []);
    assert.equal(listJobs(dir).claimed.length, 3);
    assert.equal(listJobs(dir).results.length, 3);

    // FIFO means each job leaves the queue once: a second drain runs nothing.
    const again = await drainOnce(dir, {
      owner: "relay-b",
      handle: async () => {
        throw new Error("nothing should run");
      },
    });
    assert.deepEqual(again, []);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test("a job posted behind three others drains last", async () => {
  const dir = room();
  try {
    for (const id of ["j4", "j5", "j6"]) postJob(dir, { id, agent: "worker", orders: id });
    postJob(dir, { id: "j7", agent: "worker", orders: "j7" });

    const seen = [];
    await drainOnce(dir, {
      handle: async (job) => {
        seen.push(job.id);
        return {};
      },
    });
    assert.deepEqual(seen, ["j4", "j5", "j6", "j7"]);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});
