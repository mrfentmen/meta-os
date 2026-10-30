// OS queue transport tests, step 2 (Rowan's lane): the result-fetch
// adapter in server/queue.mjs, exercised only through an injected
// stub queueGet. No test here ever touches a real queue, fires a
// live call, validates an assessment, or wires the queue into
// /api/assess. The result envelope shape is the proposed Trio-side
// shape, pending agreement with Pax's resident-agent end.

import test from "node:test";
import assert from "node:assert/strict";

import {
  QueueError,
  QUEUE_RESULT_VERSION,
  QUEUE_RESULT_KIND,
  fetchQueueResult,
} from "../server/queue.mjs";

const QUEUE_ENV = { TRIO_QUEUE_ENABLED: "1", TRIO_QUEUE_URL: "https://queue.example.invalid/jobs" };
const JOB_ID = "filed-42";

function stubQueueGet(result) {
  const calls = [];
  const fn = async (url, jobId) => {
    calls.push({ url, jobId });
    if (result instanceof Error) throw result;
    return result;
  };
  fn.calls = calls;
  return fn;
}

function doneEnvelope(assessment) {
  return {
    version: QUEUE_RESULT_VERSION,
    kind: QUEUE_RESULT_KIND,
    jobId: JOB_ID,
    status: "done",
    assessment,
  };
}

test("fetch: disabled queue refuses before any transport call", async () => {
  const get = stubQueueGet({ status: "pending" });
  await assert.rejects(
    () => fetchQueueResult(JOB_ID, {}, { queueGet: get }),
    (e) => e instanceof QueueError && e.code === "queue_disabled",
  );
  assert.equal(get.calls.length, 0);
});

test("fetch: enabled queue without a URL refuses as not configured", async () => {
  const get = stubQueueGet({ status: "pending" });
  await assert.rejects(
    () => fetchQueueResult(JOB_ID, { TRIO_QUEUE_ENABLED: "1" }, { queueGet: get }),
    (e) => e instanceof QueueError && e.code === "queue_not_configured",
  );
  assert.equal(get.calls.length, 0);
});

test("fetch: a bad job id, a missing transport, or a throwing transport all fail as queue_fetch_failed", async () => {
  await assert.rejects(
    () => fetchQueueResult("", QUEUE_ENV, { queueGet: stubQueueGet({ status: "pending" }) }),
    (e) => e instanceof QueueError && e.code === "queue_fetch_failed",
  );
  await assert.rejects(
    () => fetchQueueResult(JOB_ID, QUEUE_ENV, {}),
    (e) => e instanceof QueueError && e.code === "queue_fetch_failed",
  );
  await assert.rejects(
    () => fetchQueueResult(JOB_ID, QUEUE_ENV, { queueGet: stubQueueGet(new Error("down")) }),
    (e) => e instanceof QueueError && e.code === "queue_fetch_failed",
  );
});

test("fetch: asks the configured URL for the filed job id and returns pending as-is", async () => {
  const get = stubQueueGet({
    version: QUEUE_RESULT_VERSION,
    kind: QUEUE_RESULT_KIND,
    jobId: JOB_ID,
    status: "pending",
  });
  assert.deepEqual(await fetchQueueResult(JOB_ID, QUEUE_ENV, { queueGet: get }), {
    status: "pending",
    jobId: JOB_ID,
  });
  assert.equal(get.calls.length, 1);
  assert.equal(get.calls[0].url, "https://queue.example.invalid/jobs");
  assert.equal(get.calls[0].jobId, JOB_ID);
});

test("fetch: a done envelope returns the assessment verbatim, unvalidated here", async () => {
  const assessment = { product: "ignis", notYetValidated: true };
  const get = stubQueueGet(doneEnvelope(assessment));
  const result = await fetchQueueResult(JOB_ID, QUEUE_ENV, { queueGet: get });
  assert.deepEqual(result, { status: "done", jobId: JOB_ID, assessment });
});

test("fetch: a failed envelope returns the agent error string when it has one", async () => {
  const withError = stubQueueGet({
    version: QUEUE_RESULT_VERSION,
    kind: QUEUE_RESULT_KIND,
    jobId: JOB_ID,
    status: "failed",
    error: "resident agent could not assess this frame",
  });
  assert.deepEqual(await fetchQueueResult(JOB_ID, QUEUE_ENV, { queueGet: withError }), {
    status: "failed",
    jobId: JOB_ID,
    error: "resident agent could not assess this frame",
  });
  const withoutError = stubQueueGet({
    version: QUEUE_RESULT_VERSION,
    kind: QUEUE_RESULT_KIND,
    jobId: JOB_ID,
    status: "failed",
  });
  assert.deepEqual(await fetchQueueResult(JOB_ID, QUEUE_ENV, { queueGet: withoutError }), {
    status: "failed",
    jobId: JOB_ID,
  });
});

test("fetch: malformed envelopes fail as queue_fetch_failed, never a fabricated result", async () => {
  const bad = [
    null,
    { ...doneEnvelope({}), version: 2 },
    { ...doneEnvelope({}), kind: "something-else" },
    { ...doneEnvelope({}), jobId: "other-job" },
    { ...doneEnvelope({}), status: "mystery" },
    { ...doneEnvelope(null) },
    { ...doneEnvelope({}), status: "failed", error: 42 },
    {
      version: QUEUE_RESULT_VERSION,
      kind: QUEUE_RESULT_KIND,
      jobId: JOB_ID,
      status: "pending",
      assessment: { product: "ignis" },
    },
  ];
  // Note: the last case is a pending envelope carrying an assessment;
  // pending must return as-is (no assessment claimed), so it is NOT
  // in the failure list below — it is asserted separately.
  const failing = bad.slice(0, 7);
  for (const envelope of failing) {
    await assert.rejects(
      () => fetchQueueResult(JOB_ID, QUEUE_ENV, { queueGet: stubQueueGet(envelope) }),
      (e) => e instanceof QueueError && e.code === "queue_fetch_failed",
    );
  }
  const pendingWithAssessment = await fetchQueueResult(JOB_ID, QUEUE_ENV, {
    queueGet: stubQueueGet(bad[7]),
  });
  assert.deepEqual(pendingWithAssessment, { status: "pending", jobId: JOB_ID });
});
