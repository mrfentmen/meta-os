// The retry verb: a failed run is continued from its baton, a refused one is not re-queued.
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import { board, retryJob } from "../agents/jobs.mjs";

function boardWith(job, result) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "metaos-retry-"));
  fs.mkdirSync(path.join(root, "jobs"), { recursive: true });
  const id = (job || result || {}).id || "j1";
  if (job) fs.writeFileSync(path.join(root, "jobs", id + ".job.json"), JSON.stringify(job));
  if (result) fs.writeFileSync(path.join(root, "jobs", id + ".result.json"), JSON.stringify(result));
  return root;
}

test("a failed job is continued from the run that died", () => {
  const root = boardWith({ id: "j1", agent: "aegis", orders: "sweep" },
    { id: "j1", agent: "aegis", run: "aegis-123", code: 3, signal: null });
  const out = retryJob({ root, id: "j1" });
  assert.equal(out.ok, true);
  assert.equal(out.id, "j1-r2");
  const next = JSON.parse(fs.readFileSync(path.join(root, "jobs", "j1-r2.job.json"), "utf8"));
  assert.equal(next.continuesFrom, "aegis-123");
  assert.equal(next.retryOf, "j1");
  assert.equal(next.orders, "sweep");
});

test("a signalled job is retryable too", () => {
  const root = boardWith({ id: "j1", agent: "aegis" },
    { id: "j1", agent: "aegis", run: "aegis-9", code: null, signal: "SIGTERM" });
  assert.equal(retryJob({ root, id: "j1" }).ok, true);
});

test("a clean job is not retried", () => {
  const root = boardWith({ id: "j1", agent: "aegis" },
    { id: "j1", agent: "aegis", run: "aegis-1", code: 0, signal: null });
  const out = retryJob({ root, id: "j1" });
  assert.equal(out.ok, false);
  assert.match(out.reason, /cleanly/);
});

test("a refused job is not re-queued", () => {
  const root = boardWith({ id: "j1", agent: "rowan" },
    { id: "j1", agent: "rowan", refused: "draft-agent" });
  const out = retryJob({ root, id: "j1" });
  assert.equal(out.ok, false);
  assert.match(out.reason, /refused/);
});

test("a job with no result has not failed", () => {
  const root = boardWith({ id: "j1", agent: "aegis" }, null);
  assert.equal(retryJob({ root, id: "j1" }).ok, false);
});

test("asking twice returns the same retry", () => {
  const root = boardWith({ id: "j1", agent: "aegis" },
    { id: "j1", agent: "aegis", run: "aegis-1", code: 2, signal: null });
  const first = retryJob({ root, id: "j1" });
  const second = retryJob({ root, id: "j1" });
  assert.equal(first.id, second.id);
  assert.equal(second.existing, true);
  assert.equal(fs.readdirSync(path.join(root, "jobs")).filter((f) => f.endsWith(".job.json")).length, 2);
});

test("a retry of a retry counts up, never collides", () => {
  const root = boardWith({ id: "j1-r2", agent: "aegis" },
    { id: "j1-r2", agent: "aegis", run: "aegis-2", code: 1, signal: null });
  assert.equal(retryJob({ root, id: "j1-r2" }).id, "j1-r3");
});

test("the board still reads the re-queued job as queued", () => {
  const root = boardWith({ id: "j1", agent: "aegis" },
    { id: "j1", agent: "aegis", run: "aegis-1", code: 5, signal: null });
  retryJob({ root, id: "j1" });
  const rows = board({ root }).rows;
  assert.equal(rows.find((r) => r.id === "j1").state, "failed");
  assert.equal(rows.find((r) => r.id === "j1-r2").state, "queued");
});
