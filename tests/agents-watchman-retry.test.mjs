// A failed job is retried once, from the run that died. The retry itself is
// stamped so a persistently broken job cannot spin the board forever.
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { createWatchman } from "../agents/watchman.mjs";

function board(job, script) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "meta-watchman-retry-"));
  const jobs = path.join(root, "jobs");
  fs.mkdirSync(jobs);
  fs.writeFileSync(
    path.join(root, "registry.json"),
    JSON.stringify({ agents: [{ name: "flaky", lane: "test", command: ["repo:node", "flaky.mjs"], budget: {} }] }),
  );
  fs.writeFileSync(path.join(root, "flaky.mjs"), script);
  fs.writeFileSync(path.join(jobs, job.id + ".job.json"), JSON.stringify(job));
  return { root, jobs, watchman: createWatchman({ registryFile: path.join(root, "registry.json"), root, jobsDir: jobs }) };
}

const FAIL_ONCE = `
import fs from "node:fs";
const f = new URL("./attempts.txt", import.meta.url);
const n = fs.existsSync(f) ? Number(fs.readFileSync(f, "utf8")) : 0;
fs.writeFileSync(f, String(n + 1));
process.exit(n === 0 ? 3 : 0);
`;

const ALWAYS_FAIL = `
import fs from "node:fs";
const f = new URL("./attempts.txt", import.meta.url);
const n = fs.existsSync(f) ? Number(fs.readFileSync(f, "utf8")) : 0;
fs.writeFileSync(f, String(n + 1));
process.exit(4);
`;

const settle = () => new Promise((resolve) => setTimeout(resolve, 80));

test("a failed job is re-queued once and continued from the run that died", async () => {
  const { root, jobs, watchman } = board({ id: "f1", agent: "flaky", orders: "go" }, FAIL_ONCE);

  const first = await watchman.pollOnce();
  assert.equal(first.length, 1);
  await first[0].handle.done;
  await settle();

  const retryFile = path.join(jobs, "f1-r2.job.json");
  assert.ok(fs.existsSync(retryFile), "the retry is on the board");
  const retry = JSON.parse(fs.readFileSync(retryFile, "utf8"));
  assert.equal(retry.autoRetried, true, "the retry is stamped automatic");
  assert.equal(retry.retryOf, "f1");
  assert.equal(retry.continuesFrom, first[0].handle.runId);
  assert.ok(watchman.ledger.read().some((e) => e.event === "job-retry" && e.id === "f1"));

  const second = await watchman.pollOnce();
  assert.equal(second.length, 1, "the retry runs");
  await second[0].handle.done;
  await settle();
  const result = JSON.parse(fs.readFileSync(path.join(jobs, "f1-r2.result.json"), "utf8"));
  assert.equal(result.code, 0);
});

test("a job that keeps failing is retried once, not forever", async () => {
  const { root, jobs, watchman } = board({ id: "f2", agent: "flaky", orders: "go" }, ALWAYS_FAIL);

  const first = await watchman.pollOnce();
  await first[0].handle.done;
  await settle();
  const second = await watchman.pollOnce();
  await second[0].handle.done;
  await settle();
  const third = await watchman.pollOnce();
  await settle();

  assert.equal(third.length, 0, "nothing new is spawned after the automatic retry");
  const jobsOnBoard = fs.readdirSync(jobs).filter((f) => f.endsWith(".job.json")).sort();
  assert.deepEqual(jobsOnBoard, ["f2-r2.job.json", "f2.job.json"]);
  assert.equal(Number(fs.readFileSync(path.join(root, "attempts.txt"), "utf8")), 2);
});

test("a job that asks to continue is continued, not retried", async () => {
  // The baton queue owns the next run when the worker asked for one, so a
  // retry would fork the same work twice. (A nonzero exit is refused by
  // continue.mjs on its own merits and then retried -- that is case 2's job.)
  // The runtime spawns with cwd = the run directory, which is where a worker
  // files its continue request.
  const script = `
import fs from "node:fs";
fs.writeFileSync("continue.json", JSON.stringify({ outcome: "continue", reason: "more to do", next: "finish" }));
process.exit(0);
`;
  const { jobs, watchman } = board({ id: "f3", agent: "flaky", orders: "go" }, script);
  const first = await watchman.pollOnce();
  await first[0].handle.done;
  await settle();
  assert.ok(watchman.ledger.read().some((e) => e.event === "continue-queued"));
  assert.equal(fs.existsSync(path.join(jobs, "f3-r2.job.json")), false);
});
