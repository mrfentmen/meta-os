// Room 1 — the claim is the correctness argument, so the test races it.
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { postJob, claimJob, postResult, listJobs, drainOnce } from "../agents/room1.mjs";

const room = () => fs.mkdtempSync(path.join(os.tmpdir(), "room1-"));

test("R1 a job posted is readable and carries its id", () => {
  const dir = room();
  const { id } = postJob(dir, { agent: "a", orders: "do the thing" });
  assert.equal(listJobs(dir).unclaimed.length, 1);
  const job = claimJob(dir, id, "relay-a");
  assert.equal(job.orders, "do the thing");
  assert.equal(job.id, id);
});

test("R2 two relays claiming the same job produce one winner", () => {
  const dir = room();
  const { id } = postJob(dir, { agent: "a", orders: "x" });
  const first = claimJob(dir, id, "relay-a");
  const second = claimJob(dir, id, "relay-b");
  assert.ok(first, "the first claim wins");
  assert.equal(second, null, "the second gets nothing, not a duplicate run");
  assert.equal(listJobs(dir).unclaimed.length, 0);
  assert.equal(listJobs(dir).claimed.length, 1);
});

test("R3 draining twice runs the job once", async () => {
  const dir = room();
  postJob(dir, { id: "once", agent: "a", orders: "x" });
  let ran = 0;
  const handle = async () => { ran += 1; return { code: 0 }; };
  const one = await drainOnce(dir, { owner: "r1", handle });
  const two = await drainOnce(dir, { owner: "r1", handle });
  assert.equal(one.length, 1);
  assert.equal(two.length, 0, "the second drain has nothing unclaimed");
  assert.equal(ran, 1);
  assert.ok(fs.existsSync(path.join(dir, "once.result.json")));
});

test("R4 a handler that throws posts a failure result instead of losing the job", async () => {
  const dir = room();
  postJob(dir, { id: "boom", agent: "a", orders: "x" });
  await drainOnce(dir, { owner: "r1", handle: async () => { throw new Error("agent unavailable"); } });
  const res = JSON.parse(fs.readFileSync(path.join(dir, "boom.result.json"), "utf8"));
  assert.equal(res.ok, false);
  assert.match(res.error, /agent unavailable/);
  assert.deepEqual(listJobs(dir).unclaimed, []);
});

test("R5 results are written atomically and readable as JSON", () => {
  const dir = room();
  postResult(dir, "r5", { ok: true, result: { code: 0 } });
  const res = JSON.parse(fs.readFileSync(path.join(dir, "r5.result.json"), "utf8"));
  assert.equal(res.id, "r5");
  assert.equal(res.result.code, 0);
  assert.ok(res.posted, "the result carries when it was posted");
});

test("R6 an empty or missing room is not an error", async () => {
  const dir = path.join(room(), "not-there-yet");
  assert.deepEqual(listJobs(dir), { unclaimed: [], claimed: [], results: [] });
  assert.deepEqual(await drainOnce(dir, { owner: "r", handle: async () => ({}) }), []);
});
