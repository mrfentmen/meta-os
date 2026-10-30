// OS queue transport tests, step 3 (Rowan's lane): QUEUE-TRANSPORT-3 —
// the Pax-agreed result shape, the bounded poll loop, the production
// HTTP transports, and the handleAssess wiring with direct fallback.
// Everything here runs through injected stubs; no test touches a real
// queue or fires a live model call. The queue assessments used are
// test doubles, clearly labelled, used only to exercise the server's
// validation plumbing — a done queue assessment is still validated
// against js/schema.js before handleAssess sends it.

import test from "node:test";
import assert from "node:assert/strict";

import { handleAssess } from "../server/assess.mjs";
import {
  QueueError,
  fetchQueueResult,
  httpQueueGet,
  httpQueuePost,
  pollQueueResult,
} from "../server/queue.mjs";

const QUEUE_ENV = { TRIO_QUEUE_ENABLED: "1", TRIO_QUEUE_URL: "https://queue.example.invalid" };
const JOB_ID = "trio-test-job";

const JPEG_BYTES = Buffer.from([0xff, 0xd8, 0xff, 0xe0, 0x00, 0x10, 0x4a, 0x46, 0x49, 0x46, 0x00, 0x01, 0xff, 0xd9]);
const JPEG_URL = `data:image/jpeg;base64,${JPEG_BYTES.toString("base64")}`;
const GOOD_REQUEST = { product: "ignis", timestamp: "2026-10-28T12:00:00.000Z", image: JPEG_URL };

function validAssessment(product) {
  return {
    product,
    timestamp: "2026-10-28T12:00:01.000Z",
    observations: [
      { category: "visible smoke", description: "Grey plume above the roofline.", evidence: "upper third of frame", confidence: 0.8 },
    ],
    assessment: {
      category: "visible smoke",
      summary: "Smoke visible; no flame in frame.",
      uncertainty: ["Distance to source unknown."],
      requires_human_review: true,
    },
    processing: { model: "test-double", latency_ms: 12 },
  };
}

function paxEnvelope(overrides = {}) {
  return {
    job_id: JOB_ID,
    status: "ok",
    assessment: validAssessment("ignis"),
    error: null,
    model: "muse-spark-1.3",
    latency_ms: 3000,
    completed_at: "2026-10-30T01:30:00.000Z",
    ...overrides,
  };
}

function stubQueueGet(sequence) {
  const calls = [];
  let i = 0;
  const fn = async (url, jobId) => {
    calls.push({ url, jobId });
    const next = sequence[Math.min(i, sequence.length - 1)];
    i += 1;
    if (next instanceof Error) throw next;
    return next;
  };
  fn.calls = calls;
  return fn;
}

test("fetch: Pax-agreed ok envelope normalizes to done with the assessment verbatim", async () => {
  const result = await fetchQueueResult(JOB_ID, QUEUE_ENV, { queueGet: stubQueueGet([paxEnvelope()]) });
  assert.equal(result.status, "done");
  assert.equal(result.jobId, JOB_ID);
  assert.deepEqual(result.assessment, validAssessment("ignis"));
  assert.equal(result.model, "muse-spark-1.3");
  assert.equal(result.latency_ms, 3000);
});

test("fetch: Pax failed envelope normalizes to failed with the agent error; Pax pending stays pending", async () => {
  const failed = await fetchQueueResult(JOB_ID, QUEUE_ENV, {
    queueGet: stubQueueGet([paxEnvelope({ status: "failed", assessment: null, error: "agent could not assess" })]),
  });
  assert.deepEqual(
    { status: failed.status, jobId: failed.jobId, error: failed.error },
    { status: "failed", jobId: JOB_ID, error: "agent could not assess" },
  );
  const pending = await fetchQueueResult(JOB_ID, QUEUE_ENV, {
    queueGet: stubQueueGet([paxEnvelope({ status: "pending", assessment: null, error: null })]),
  });
  assert.equal(pending.status, "pending");
  assert.equal(pending.jobId, JOB_ID);
});

test("fetch: malformed Pax envelopes fail as queue_fetch_failed, never a fabricated result", async () => {
  const bad = [
    paxEnvelope({ job_id: "other-job" }),
    paxEnvelope({ status: "ok", assessment: null }),
    paxEnvelope({ status: "ok", assessment: { product: "ignis" }, error: "both" }),
    paxEnvelope({ status: "failed", assessment: validAssessment("ignis") }),
    paxEnvelope({ status: "failed", error: 42 }),
    paxEnvelope({ status: "mystery" }),
    paxEnvelope({ model: 42 }),
    null,
  ];
  for (const envelope of bad) {
    await assert.rejects(
      () => fetchQueueResult(JOB_ID, QUEUE_ENV, { queueGet: stubQueueGet([envelope]) }),
      (e) => e instanceof QueueError && e.code === "queue_fetch_failed",
    );
  }
});

test("poll: pending then ok returns done, counting only the fetches it needed", async () => {
  const get = stubQueueGet([
    paxEnvelope({ status: "pending", assessment: null, error: null }),
    paxEnvelope({ status: "pending", assessment: null, error: null }),
    paxEnvelope(),
  ]);
  const result = await pollQueueResult(JOB_ID, QUEUE_ENV, {
    queueGet: get,
    pollIntervalMs: 0,
    maxAttempts: 5,
    sleep: async () => {},
  });
  assert.equal(result.status, "done");
  assert.equal(get.calls.length, 3);
});

test("poll: a failed result returns immediately without further fetches", async () => {
  const get = stubQueueGet([paxEnvelope({ status: "failed", assessment: null, error: "agent error" })]);
  const result = await pollQueueResult(JOB_ID, QUEUE_ENV, {
    queueGet: get,
    pollIntervalMs: 0,
    maxAttempts: 5,
    sleep: async () => {},
  });
  assert.equal(result.status, "failed");
  assert.equal(get.calls.length, 1);
});

test("poll: a pending streak that exhausts the bound throws queue_fetch_failed", async () => {
  const get = stubQueueGet([paxEnvelope({ status: "pending", assessment: null, error: null })]);
  await assert.rejects(
    () =>
      pollQueueResult(JOB_ID, QUEUE_ENV, {
        queueGet: get,
        pollIntervalMs: 0,
        maxAttempts: 3,
        sleep: async () => {},
      }),
    (e) => e instanceof QueueError && e.code === "queue_fetch_failed" && /timed out/.test(e.message),
  );
  assert.equal(get.calls.length, 3);
});

test("poll: disabled or not-configured propagates immediately, never loops", async () => {
  await assert.rejects(
    () =>
      pollQueueResult(JOB_ID, {}, {
        queueGet: stubQueueGet([paxEnvelope()]),
        maxAttempts: 5,
        sleep: async () => {},
      }),
    (e) => e instanceof QueueError && e.code === "queue_disabled",
  );
});

test("http transports: post goes to base/jobs and echoes jobId/id/job_id; get 404 means pending", async () => {
  const posts = [];
  const post = await httpQueuePost("https://queue.example.invalid/", { kind: "trio-assessment" }, {
    fetch: async (url, opts) => {
      posts.push({ url, opts });
      return { ok: true, json: async () => ({ id: "filed-1" }) };
    },
  });
  assert.deepEqual(post, { jobId: "filed-1" });
  assert.equal(posts[0].url, "https://queue.example.invalid/jobs");
  assert.equal(posts[0].opts.method, "POST");

  const pending = await httpQueueGet("https://queue.example.invalid", JOB_ID, {
    fetch: async (url) => {
      assert.equal(url, `https://queue.example.invalid/jobs/${JOB_ID}/result`);
      return { ok: false, status: 404 };
    },
  });
  assert.deepEqual(pending, { job_id: JOB_ID, status: "pending", assessment: null, error: null });

  await assert.rejects(
    () =>
      httpQueueGet("https://queue.example.invalid", JOB_ID, {
        fetch: async () => ({ ok: false, status: 500 }),
      }),
    (e) => e instanceof QueueError && e.code === "queue_fetch_failed",
  );
});

test("wiring: a done queue assessment is returned validated, and the direct model is never called", async () => {
  let modelCalls = 0;
  const logs = [];
  const { status, body } = await handleAssess(GOOD_REQUEST, {
    env: QUEUE_ENV,
    log: (msg) => logs.push(msg),
    assessModel: async () => {
      modelCalls += 1;
      return validAssessment("ignis");
    },
    queue: {
      queuePost: async () => ({ jobId: JOB_ID }),
      queueGet: stubQueueGet([paxEnvelope()]),
      pollIntervalMs: 0,
      maxAttempts: 3,
      sleep: async () => {},
    },
  });
  assert.equal(status, 200);
  assert.equal(body.processing.model, "test-double");
  assert.equal(modelCalls, 0);
  assert.equal(logs.length, 0);
});

test("wiring: a queue submit failure falls back to the direct path and logs the fallback", async () => {
  let modelCalls = 0;
  const logs = [];
  const { status, body } = await handleAssess(GOOD_REQUEST, {
    env: QUEUE_ENV,
    log: (msg) => logs.push(msg),
    assessModel: async (input) => {
      modelCalls += 1;
      return validAssessment(input.product);
    },
    queue: {
      queuePost: async () => {
        throw new Error("queue down");
      },
      queueGet: stubQueueGet([paxEnvelope()]),
      sleep: async () => {},
    },
  });
  assert.equal(status, 200);
  assert.equal(modelCalls, 1);
  assert.equal(logs.length, 1);
  assert.match(logs[0], /queue fallback/);
});

test("wiring: a queue poll timeout falls back to the direct path", async () => {
  const logs = [];
  const { status } = await handleAssess(GOOD_REQUEST, {
    env: QUEUE_ENV,
    log: (msg) => logs.push(msg),
    assessModel: async (input) => validAssessment(input.product),
    queue: {
      queuePost: async () => ({ jobId: JOB_ID }),
      queueGet: stubQueueGet([paxEnvelope({ status: "pending", assessment: null, error: null })]),
      pollIntervalMs: 0,
      maxAttempts: 2,
      sleep: async () => {},
    },
  });
  assert.equal(status, 200);
  assert.equal(logs.length, 1);
  assert.match(logs[0], /timed out/);
});

test("wiring: a failed queue result falls back to the direct path", async () => {
  const { status } = await handleAssess(GOOD_REQUEST, {
    env: QUEUE_ENV,
    log: () => {},
    assessModel: async (input) => validAssessment(input.product),
    queue: {
      queuePost: async () => ({ jobId: JOB_ID }),
      queueGet: stubQueueGet([paxEnvelope({ status: "failed", assessment: null, error: "agent error" })]),
      sleep: async () => {},
    },
  });
  assert.equal(status, 200);
});

test("wiring: a done queue assessment that fails contract validation is a 502, not a silent fallback", async () => {
  let modelCalls = 0;
  const { status, body } = await handleAssess(GOOD_REQUEST, {
    env: QUEUE_ENV,
    log: () => {},
    assessModel: async () => {
      modelCalls += 1;
      return validAssessment("ignis");
    },
    queue: {
      queuePost: async () => ({ jobId: JOB_ID }),
      queueGet: stubQueueGet([paxEnvelope({ assessment: { product: "ignis", timestamp: "nope" } })]),
      sleep: async () => {},
    },
  });
  assert.equal(status, 502);
  assert.match(body.error, /contract validation/);
  assert.equal(modelCalls, 0);
});

test("wiring: queue disabled never calls queue transports and runs the direct path alone", async () => {
  let postCalls = 0;
  const { status } = await handleAssess(GOOD_REQUEST, {
    env: {},
    assessModel: async (input) => validAssessment(input.product),
    queue: {
      queuePost: async () => {
        postCalls += 1;
        return { jobId: JOB_ID };
      },
      queueGet: stubQueueGet([paxEnvelope()]),
      sleep: async () => {},
    },
  });
  assert.equal(status, 200);
  assert.equal(postCalls, 0);
});
