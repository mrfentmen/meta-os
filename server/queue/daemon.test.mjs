// daemon.test.mjs — tests for the metaosd agent daemon (R2-T3 Section B).
// Node stdlib only: `node --test server/queue/daemon.test.mjs`
// Data dirs are temp dirs OUTSIDE the git tree (os.tmpdir()).

import assert from "node:assert";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { after, describe, it } from "node:test";
import url from "node:url";

import {
  atomicWrite,
  chainPrev,
  checkWritable,
  cleanStaleLock,
  dataPaths,
  loadIdem,
  loadOrCreateKey,
  readKey,
  receiptHmac,
  saveIdem,
  verifyChain,
  verifyReceiptObject,
} from "./metaosd_store.mjs";
import { createDaemon, createServer } from "../../os-build/iso/payload-agent/metaosd.mjs";

const HERE = path.dirname(url.fileURLToPath(import.meta.url));
const SCHEMA = path.join(HERE, "..", "..", "agents", "job.schema.json");

function tmpData() {
  return fs.mkdtempSync(path.join(os.tmpdir(), "metaosd-test-"));
}

async function liveDaemon(t, opts = {}) {
  const dataDir = tmpData();
  t.after(() => {
    fs.rmSync(dataDir, { recursive: true, force: true });
  });
  const daemon = createDaemon({
    dataDir,
    poolSize: opts.poolSize || 2,
    agentCap: opts.agentCap || 2,
    schemaFile: SCHEMA,
  });
  const server = createServer(daemon, { port: 0 });
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  const port = server.address().port;
  t.after(async () => {
    await new Promise((resolve) => server.close(resolve));
    daemon.shutdown();
    await new Promise((r) => setTimeout(r, 150)); // let in-flight children die
    fs.rmSync(dataDir, { recursive: true, force: true });
  });
  const base = "http://127.0.0.1:" + port;
  return { dataDir, daemon, base };
}

async function submit(base, job, key) {
  const headers = { "Content-Type": "application/json" };
  if (key) headers["Idempotency-Key"] = key;
  const res = await fetch(base + "/jobs", { method: "POST", headers, body: JSON.stringify(job) });
  return { status: res.status, body: await res.json() };
}

async function waitFor(base, id, want, timeoutMs = 15000) {
  const end = Date.now() + timeoutMs;
  for (;;) {
    const res = await fetch(base + "/jobs/" + id + "/status");
    const snap = await res.json();
    if (want.includes(snap.status)) return snap;
    if (Date.now() > end) throw new Error("timed out waiting for " + id + " to reach " + want + " (at " + snap.status + ")");
    await new Promise((r) => setTimeout(r, 100));
  }
}

describe("job schema (agents/job.schema.json, single copy)", () => {
  it("daemon submit accepts the six-field shape", async (t) => {
    const { base } = await liveDaemon(t);
    const { status, body } = await submit(base, { agent: "a1", input: { sleepMs: 10 } });
    assert.equal(status, 201);
    assert.match(body.id, /^job-/);
  });

  it("unknown top-level fields are refused BY NAME", async (t) => {
    const { base } = await liveDaemon(t);
    const { status, body } = await submit(base, { agent: "a1", frobnicate: 1 });
    assert.equal(status, 400);
    assert.match(body.error, /frobnicate/);
  });

  it("unknown budget fields are refused BY NAME", async (t) => {
    const { base } = await liveDaemon(t);
    const { status, body } = await submit(base, { agent: "a1", budget: { warpSpeed: 9 } });
    assert.equal(status, 400);
    assert.match(body.error, /warpSpeed/);
  });

  it("missing agent and bad id are refused", async (t) => {
    const { base } = await liveDaemon(t);
    const r1 = await submit(base, { input: {} });
    assert.equal(r1.status, 400);
    assert.match(r1.body.error, /agent/);
    const r2 = await submit(base, { agent: "a1", id: "../evil" });
    assert.equal(r2.status, 400);
  });
});

describe("idempotency (request key)", () => {
  it("double submit with one key yields one job", async (t) => {
    const { base, daemon } = await liveDaemon(t);
    const first = await submit(base, { agent: "a1", input: { sleepMs: 10 } }, "req-123");
    const second = await submit(base, { agent: "a1", input: { sleepMs: 10 } }, "req-123");
    assert.equal(first.status, 201);
    assert.equal(second.status, 200);
    assert.equal(first.body.id, second.body.id);
    assert.equal(second.body.existing, true);
    assert.equal(daemon.list().length, 1);
  });

  it("idempotency map survives reload (durable file)", async (t) => {
    const dir = tmpData();
    t.after(() => fs.rmSync(dir, { recursive: true, force: true }));
    fs.mkdirSync(dataPaths(dir).jobs, { recursive: true });
    fs.mkdirSync(dataPaths(dir).runs, { recursive: true });
    saveIdem(dir, { "k-1": "job-x" });
    assert.deepEqual(loadIdem(dir), { "k-1": "job-x" });
  });
});

describe("run records + dry-run", () => {
  it("a job completes with a run record, artifacts relative to the run dir", async (t) => {
    const { base, dataDir } = await liveDaemon(t);
    const { body } = await submit(base, {
      agent: "a1",
      input: { sleepMs: 50, artifact: { name: "result.txt", content: "hello" } },
    });
    const snap = await waitFor(base, body.id, ["succeeded"]);
    assert.equal(snap.spawned, true);
    assert.equal(snap.artifactsRelativeTo, "runs/" + body.id);
    const runDir = path.join(dataPaths(dataDir).runs, body.id);
    assert.ok(fs.existsSync(path.join(runDir, "output-attempt1.log")));
    assert.ok(fs.existsSync(path.join(runDir, "result.txt")));
    assert.ok(fs.existsSync(path.join(runDir, "receipt.json")));
    assert.ok(snap.startedAt && snap.endedAt && snap.exit);
  });

  it("dry-run writes a record, spawns nothing, contacts no model", async (t) => {
    const { base, daemon } = await liveDaemon(t);
    const { status, body } = await submit(base, { agent: "a1", "dry-run": true });
    assert.equal(status, 201);
    const res = await fetch(base + "/jobs/" + body.id);
    const rec = await res.json();
    assert.equal(rec.status, "dryrun");
    assert.equal(rec.spawned, false);
    assert.equal(rec.command, null);
    assert.equal(daemon.get(body.id).spawned, false);
  });
});

describe("timeout + cancel + retry", () => {
  it("per-job timeout kills the child and records a timeout failure", async (t) => {
    const { base } = await liveDaemon(t);
    const { body } = await submit(base, { agent: "a1", input: { sleepMs: 30000 }, timeout: 300 });
    const snap = await waitFor(base, body.id, ["timeout"], 10000);
    assert.equal(snap.attempts[0].state, "timeout");
  });

  it("cancel leaves a cancelled record", async (t) => {
    const { base } = await liveDaemon(t);
    const { body } = await submit(base, { agent: "a1", input: { sleepMs: 20000 } });
    await new Promise((r) => setTimeout(r, 400)); // let it start
    const res = await fetch(base + "/jobs/" + body.id + "/cancel", { method: "POST" });
    assert.ok([200].includes(res.status));
    const snap = await waitFor(base, body.id, ["cancelled"], 10000);
    assert.equal(snap.status, "cancelled");
    // The record still exists.
    const rec = await (await fetch(base + "/jobs/" + body.id)).json();
    assert.equal(rec.id, body.id);
  });

  it("retry honors maxAttempts with visible backoff", async (t) => {
    const { base } = await liveDaemon(t);
    const { body } = await submit(base, {
      agent: "a1",
      input: { sleepMs: 5, exitCode: 3 },
      budget: { maxAttempts: 2, backoffMs: 200 },
    });
    const snap = await waitFor(base, body.id, ["failed"], 15000);
    assert.equal(snap.attempts.length, 2); // one automatic retry happened
    assert.ok(snap.attempts[1].backoffWaitedMs >= 150, "backoff visible: " + snap.attempts[1].backoffWaitedMs);
    const again = await fetch(base + "/jobs/" + body.id + "/retry", { method: "POST" });
    assert.equal(again.status, 409); // exhausted
    assert.match((await again.json()).error, /maxAttempts=2/);
  });
});

describe("pool + per-agent cap + health", () => {
  it("per-agent cap refuses by name; health shows busy state", async (t) => {
    const { base } = await liveDaemon(t, { poolSize: 4, agentCap: 1 });
    const a = await submit(base, { agent: "solo", input: { sleepMs: 2000 } });
    assert.equal(a.status, 201);
    await new Promise((r) => setTimeout(r, 400));
    const refused = await submit(base, { agent: "solo", input: {} });
    assert.equal(refused.status, 429);
    assert.match(refused.body.error, /agent-concurrency-cap/);
    assert.match(refused.body.error, /solo/);
    const health = await (await fetch(base + "/health")).json();
    assert.equal(health.ok, true);
    assert.ok(health.workers.busy.includes(a.body.id));
    assert.equal(health.workers.perAgent.solo, 1);
    assert.ok(health.queueDepth >= 0 && health.oldestJobAgeMs !== undefined);
  });

  it("queue depth + oldest-job age appear in /health", async (t) => {
    const { base } = await liveDaemon(t, { poolSize: 1, agentCap: 10 });
    await submit(base, { agent: "q", input: { sleepMs: 1500 } });
    await submit(base, { agent: "q", input: { sleepMs: 10 } });
    await new Promise((r) => setTimeout(r, 300));
    const health = await (await fetch(base + "/health")).json();
    assert.ok(health.queueDepth >= 1);
    assert.ok(typeof health.oldestJobAgeMs === "number" && health.oldestJobAgeMs >= 0);
  });
});

describe("list filters + poll contract", () => {
  it("GET /jobs filters by agent/status/date", async (t) => {
    const { base } = await liveDaemon(t);
    const j1 = await submit(base, { agent: "alpha", input: { sleepMs: 5 } });
    await submit(base, { agent: "beta", "dry-run": true });
    await waitFor(base, j1.body.id, ["succeeded"]);
    const byAgent = await (await fetch(base + "/jobs?agent=alpha")).json();
    assert.ok(byAgent.count >= 1 && byAgent.jobs.every((j) => j.agent === "alpha"));
    const dry = await (await fetch(base + "/jobs?status=dryrun")).json();
    assert.ok(dry.jobs.every((j) => j.status === "dryrun"));
    const since = await (await fetch(base + "/jobs?since=2000-01-01T00:00:00.000Z")).json();
    assert.ok(since.count >= 2);
    const none = await (await fetch(base + "/jobs?since=2999-01-01T00:00:00.000Z")).json();
    assert.equal(none.count, 0);
  });

  it("status shape carries the poll contract fields", async (t) => {
    const { base } = await liveDaemon(t);
    const { body } = await submit(base, { agent: "p", input: { sleepMs: 5 } });
    const snap = await waitFor(base, body.id, ["succeeded"]);
    for (const f of ["id", "agent", "status", "attempt", "attempts", "startedAt", "endedAt", "exit", "updatedAt"]) {
      assert.ok(snap[f] !== undefined, "status missing field " + f);
    }
  });
});

describe("receipts + verify", () => {
  it("one tampered byte fails verification (hmac mismatch)", () => {
    const dir = tmpData();
    try {
      fs.mkdirSync(dataPaths(dir).jobs, { recursive: true });
      const { key } = loadOrCreateKey(dir);
      const fields = { job: "j1", prev: "GENESIS" };
      const hmac = receiptHmac(key, fields);
      assert.ok(verifyReceiptObject(key, { ...fields, hmac }, "GENESIS").ok);
      const bad = { ...fields, hmac: hmac.slice(0, -1) + (hmac.endsWith("0") ? "1" : "0") };
      const v = verifyReceiptObject(key, bad, "GENESIS");
      assert.equal(v.ok, false);
      assert.match(v.error, /hmac mismatch/);
    } finally {
      fs.rmSync(dir, { recursive: true, force: true });
    }
  });

  it("verify refuses without a receipt key, naming its path", async (t) => {
    const { base, dataDir } = await liveDaemon(t);
    const { body } = await submit(base, { agent: "v", "dry-run": true });
    fs.unlinkSync(path.join(dataDir, "receipt.key")); // simulate key loss
    const res = await fetch(base + "/verify?job=" + body.id);
    assert.equal(res.status, 400);
    const out = await res.json();
    assert.match(out.error, /no receipt key at /);
    assert.ok(out.keyPath.endsWith("receipt.key"));
    const chain = verifyChain(dataDir);
    assert.equal(chain.ok, false);
    assert.match(chain.error, /no receipt key at /);
  });

  it("chain linkage is checked in order", () => {
    const dir = tmpData();
    try {
      fs.mkdirSync(dataPaths(dir).jobs, { recursive: true });
      const { key } = loadOrCreateKey(dir);
      let prev = chainPrev(dir);
      assert.equal(prev, "GENESIS");
      for (const j of ["j1", "j2"]) {
        const fields = { job: j, prev };
        const hmac = receiptHmac(key, fields);
        fs.appendFileSync(dataPaths(dir).chain, JSON.stringify({ ...fields, hmac }) + "\n");
        prev = hmac;
      }
      assert.equal(verifyChain(dir).checked, 2);
    } finally {
      fs.rmSync(dir, { recursive: true, force: true });
    }
  });
});

describe("startup guards", () => {
  it("stale lock is cleaned and reported; live lock refuses", () => {
    const dir = tmpData();
    try {
      fs.mkdirSync(dir, { recursive: true });
      fs.writeFileSync(dataPaths(dir).lock, JSON.stringify({ pid: 987654321, startedAt: "long ago" }));
      const cleaned = cleanStaleLock(dir);
      assert.ok(cleaned.removed && cleaned.removed.path.endsWith("metaosd.lock"));
      assert.equal(cleaned.removed.pid, 987654321);
      assert.ok(!fs.existsSync(dataPaths(dir).lock));
      fs.writeFileSync(dataPaths(dir).lock, JSON.stringify({ pid: process.pid, startedAt: "now" }));
      const live = cleanStaleLock(dir);
      assert.equal(live.removed, null);
      assert.equal(live.active.pid, process.pid);
    } finally {
      fs.rmSync(dir, { recursive: true, force: true });
    }
  });

  it("unwritable data dir is detected", () => {
    const w = checkWritable("/proc/metaosd-nope-" + process.pid);
    assert.equal(w.ok, false);
  });

  it("atomicWrite round-trips a record", () => {
    const dir = tmpData();
    try {
      fs.mkdirSync(dir, { recursive: true });
      atomicWrite(path.join(dir, "r.json"), "{\"a\":1}");
      assert.deepEqual(JSON.parse(fs.readFileSync(path.join(dir, "r.json"), "utf8")), { a: 1 });
    } finally {
      fs.rmSync(dir, { recursive: true, force: true });
    }
  });
});
