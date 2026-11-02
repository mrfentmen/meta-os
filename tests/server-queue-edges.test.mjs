// Queue transport edge cases beyond steps 1–3: the refusal paths that
// are only reachable with odd transports, odd envelopes, and a zero
// poll bound. Every transport is an injected stub; no test touches a
// real queue and no failure path is allowed to leak a fabricated
// assessment.
// Run: node --test tests/server-queue-edges.test.mjs

import test from "node:test";
import assert from "node:assert/strict";

import {
  QueueError,
  buildQueueJob,
  queueConfig,
  submitQueueJob,
  fetchQueueResult,
  pollQueueResult,
  httpQueuePost,
  httpQueueGet,
} from "../server/queue.mjs";

const JPEG_BYTES = Buffer.from([0xff, 0xd8, 0xff, 0xe0, 0x00, 0x10, 0x4a, 0x46, 0x49, 0x46, 0x00, 0x01, 0xff, 0xd9]);
const INPUT = {
  product: "ignis",
  timestamp: "2026-11-02T12:00:00.000Z",
  imageBytes: JPEG_BYTES,
  mediaType: "image/jpeg",
};
const ENV = { TRIO_QUEUE_ENABLED: "1", TRIO_QUEUE_URL: "https://queue.example.invalid" };
const JOB_ID = "trio-edge-job";

function stubPost(result) {
  const calls = [];
  const fn = async (url, job) => {
    calls.push({ url, job });
    if (result instanceof Error) throw result;
    return result;
  };
  fn.calls = calls;
  return fn;
}

function stubGet(result) {
  const calls = [];
  const fn = async (url, jobId) => {
    calls.push({ url, jobId });
    if (result instanceof Error) throw result;
    return result;
  };
  fn.calls = calls;
  return fn;
}

const isQueueError = (code) => (e) => e instanceof QueueError && e.code === code;

test("config: only the exact string '1' enables the queue, and a non-string URL is empty", () => {
  assert.deepEqual(queueConfig({ TRIO_QUEUE_ENABLED: "true", TRIO_QUEUE_URL: "https://q.invalid" }), {
    enabled: false,
    url: "https://q.invalid",
  });
  assert.deepEqual(queueConfig({ TRIO_QUEUE_ENABLED: "1", TRIO_QUEUE_URL: 42 }), {
    enabled: true,
    url: "",
  });
});

test("buildQueueJob always stamps image/jpeg and binds the id to product + timestamp + frame", () => {
  const job = buildQueueJob({ ...INPUT, mediaType: "image/png" });
  assert.equal(job.image.mediaType, "image/jpeg");
  const again = buildQueueJob(INPUT);
  assert.equal(again.id, job.id, "mediaType is not part of the id");
  assert.notEqual(buildQueueJob({ ...INPUT, product: "vigiles" }).id, job.id);
  assert.notEqual(buildQueueJob({ ...INPUT, timestamp: "2026-11-02T12:00:00.001Z" }).id, job.id);
});

test("buildQueueJob rejects a non-buffer image value and a missing product", () => {
  assert.throws(
    () => buildQueueJob({ ...INPUT, imageBytes: null }),
    isQueueError("queue_submit_failed"),
  );
  assert.throws(
    () => buildQueueJob({ ...INPUT, product: undefined }),
    isQueueError("queue_submit_failed"),
  );
});

test("submit refuses every malformed envelope shape before calling the transport", async () => {
  const job = buildQueueJob(INPUT);
  const badJobs = [
    { ...job, version: 2 },
    { ...job, kind: "something-else" },
    { ...job, id: "" },
    { ...job, image: { ...job.image, dataUrl: "data:image/png;base64,AAAA" } },
  ];
  for (const bad of badJobs) {
    const post = stubPost({ jobId: "q-1" });
    await assert.rejects(
      () => submitQueueJob(bad, ENV, { queuePost: post }),
      isQueueError("queue_submit_failed"),
    );
    assert.equal(post.calls.length, 0);
  }
});

test("submit rethrows a QueueError from the transport unchanged, and wraps a plain error", async () => {
  const job = buildQueueJob(INPUT);
  const typed = new QueueError("queue_submit_failed", "transport said no");
  await assert.rejects(
    () => submitQueueJob(job, ENV, { queuePost: stubPost(typed) }),
    (e) => e === typed,
  );
  await assert.rejects(
    () => submitQueueJob(job, ENV, { queuePost: stubPost(new Error("socket closed")) }),
    (e) => e instanceof QueueError && e.code === "queue_submit_failed" && /socket closed/.test(e.message),
  );
});

test("submit treats a null transport result as no job id", async () => {
  await assert.rejects(
    () => submitQueueJob(buildQueueJob(INPUT), ENV, { queuePost: stubPost(null) }),
    (e) => e instanceof QueueError && e.code === "queue_submit_failed" && /no job id/.test(e.message),
  );
});

test("fetch rejects a non-string job id before any transport call", async () => {
  const get = stubGet({ job_id: JOB_ID, status: "pending" });
  await assert.rejects(
    () => fetchQueueResult(42, ENV, { queueGet: get }),
    isQueueError("queue_fetch_failed"),
  );
  assert.equal(get.calls.length, 0);
});

test("fetch passes model/latency/completed_at through, including explicit nulls", async () => {
  const assessment = { product: "ignis" };
  const result = await fetchQueueResult(JOB_ID, ENV, {
    queueGet: stubGet({
      job_id: JOB_ID,
      status: "ok",
      assessment,
      error: null,
      model: null,
      latency_ms: null,
      completed_at: "2026-11-02T12:00:01.000Z",
    }),
  });
  assert.deepEqual(result, {
    status: "done",
    jobId: JOB_ID,
    assessment,
    model: null,
    latency_ms: null,
    completed_at: "2026-11-02T12:00:01.000Z",
  });
});

test("fetch rejects non-object envelopes and a non-string completed_at", async () => {
  const bad = [
    [],
    "not an object",
    42,
    { job_id: JOB_ID, status: "ok", assessment: {}, completed_at: 7 },
    { version: 1, jobId: JOB_ID }, // version present but kind absent
  ];
  for (const envelope of bad) {
    await assert.rejects(
      () => fetchQueueResult(JOB_ID, ENV, { queueGet: stubGet(envelope) }),
      (e) => e instanceof QueueError && e.code === "queue_fetch_failed" && e.assessment === undefined,
    );
  }
});

test("http submit names each failure: HTTP status, non-JSON body, missing id, network error", async () => {
  const job = buildQueueJob(INPUT);
  await assert.rejects(
    () => httpQueuePost("https://q.invalid", job, { fetch: async () => ({ ok: false, status: 503 }) }),
    (e) => /HTTP 503/.test(e.message),
  );
  await assert.rejects(
    () => httpQueuePost("https://q.invalid", job, {
      fetch: async () => ({ ok: true, json: async () => { throw new Error("bad body"); } }),
    }),
    (e) => /not JSON/.test(e.message),
  );
  await assert.rejects(
    () => httpQueuePost("https://q.invalid", job, {
      fetch: async () => ({ ok: true, json: async () => ({ nope: true }) }),
    }),
    (e) => /no job id/.test(e.message),
  );
  await assert.rejects(
    () => httpQueuePost("https://q.invalid", job, {
      fetch: async () => { throw new Error("connection refused"); },
    }),
    (e) => e instanceof QueueError && e.code === "queue_submit_failed" && /connection refused/.test(e.message),
  );
});

test("http result fetch wraps a network error and rejects a non-JSON body", async () => {
  await assert.rejects(
    () => httpQueueGet("https://q.invalid", JOB_ID, {
      fetch: async () => { throw new Error("dns failed"); },
    }),
    (e) => e instanceof QueueError && e.code === "queue_fetch_failed" && /dns failed/.test(e.message),
  );
  await assert.rejects(
    () => httpQueueGet("https://q.invalid", JOB_ID, {
      fetch: async () => ({ ok: true, status: 200, json: async () => { throw new Error("bad"); } }),
    }),
    (e) => e instanceof QueueError && e.code === "queue_fetch_failed" && /not JSON/.test(e.message),
  );
});

test("poll with one attempt fetches once; a zero bound fetches nothing and still times out", async () => {
  const one = stubGet({ job_id: JOB_ID, status: "pending" });
  await assert.rejects(
    () => pollQueueResult(JOB_ID, ENV, { queueGet: one, maxAttempts: 1, sleep: async () => {} }),
    (e) => e instanceof QueueError && e.code === "queue_fetch_failed" && /after 1 attempts/.test(e.message),
  );
  assert.equal(one.calls.length, 1);

  const zero = stubGet({ job_id: JOB_ID, status: "pending" });
  await assert.rejects(
    () => pollQueueResult(JOB_ID, ENV, { queueGet: zero, maxAttempts: 0, sleep: async () => {} }),
    (e) => e instanceof QueueError && e.code === "queue_fetch_failed" && /after 0 attempts/.test(e.message),
  );
  assert.equal(zero.calls.length, 0);
});
