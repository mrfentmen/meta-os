// OS queue transport tests, step 1 (Rowan's lane): the job envelope
// and the submit adapter in server/queue.mjs, exercised only through
// an injected stub queuePost. No test here ever touches a real queue,
// fires a live call, or wires the queue into /api/assess.

import test from "node:test";
import assert from "node:assert/strict";
import { createHash } from "node:crypto";

import {
  QueueError,
  QUEUE_JOB_VERSION,
  QUEUE_JOB_KIND,
  buildQueueJob,
  queueConfig,
  submitQueueJob,
} from "../server/queue.mjs";

// Minimal bytes carrying the JPEG magic prefix; the envelope carries
// the frame, not a picture — interpreting pixels is the model's job.
const JPEG_BYTES = Buffer.from([0xff, 0xd8, 0xff, 0xe0, 0x00, 0x10, 0x4a, 0x46, 0x49, 0x46, 0x00, 0x01, 0xff, 0xd9]);
const INPUT = {
  product: "ignis",
  timestamp: "2026-10-28T12:00:00.000Z",
  imageBytes: JPEG_BYTES,
  mediaType: "image/jpeg",
};
const QUEUE_ENV = { TRIO_QUEUE_ENABLED: "1", TRIO_QUEUE_URL: "https://queue.example.invalid/jobs" };

function stubQueuePost(result) {
  const calls = [];
  const fn = async (url, job) => {
    calls.push({ url, job });
    if (result instanceof Error) throw result;
    return result;
  };
  fn.calls = calls;
  return fn;
}

test("envelope: carries product, timestamp, frame data URL, byte length, and SHA-256 of the frame", () => {
  const job = buildQueueJob(INPUT);
  assert.equal(job.version, QUEUE_JOB_VERSION);
  assert.equal(job.kind, QUEUE_JOB_KIND);
  assert.equal(job.product, "ignis");
  assert.equal(job.timestamp, "2026-10-28T12:00:00.000Z");
  assert.equal(job.image.mediaType, "image/jpeg");
  assert.equal(job.image.byteLength, JPEG_BYTES.length);
  assert.equal(job.image.sha256, createHash("sha256").update(JPEG_BYTES).digest("hex"));
  assert.equal(job.image.dataUrl, `data:image/jpeg;base64,${JPEG_BYTES.toString("base64")}`);
  assert.match(job.id, /^trio-[0-9a-f]{32}$/);
});

test("envelope: the id is deterministic for the same frame and changes with a different frame", () => {
  const again = buildQueueJob(INPUT);
  assert.equal(again.id, buildQueueJob(INPUT).id);
  const other = buildQueueJob({ ...INPUT, imageBytes: Buffer.from([0xff, 0xd8, 0xff, 0xe1, 0x00]) });
  assert.notEqual(other.id, again.id);
});

test("envelope: bad inputs throw queue_submit_failed, never a half-built job", () => {
  assert.throws(() => buildQueueJob(null), (e) => e instanceof QueueError && e.code === "queue_submit_failed");
  assert.throws(() => buildQueueJob({ ...INPUT, product: "vigiles-x" }), (e) => e instanceof QueueError && e.code === "queue_submit_failed");
  assert.throws(() => buildQueueJob({ ...INPUT, timestamp: "" }), (e) => e instanceof QueueError && e.code === "queue_submit_failed");
  assert.throws(() => buildQueueJob({ ...INPUT, imageBytes: Buffer.alloc(0) }), (e) => e instanceof QueueError && e.code === "queue_submit_failed");
});

test("config: disabled by default, enabled only with TRIO_QUEUE_ENABLED=1 and a URL", () => {
  assert.deepEqual(queueConfig({}), { enabled: false, url: "" });
  assert.deepEqual(queueConfig({ TRIO_QUEUE_ENABLED: "1" }), { enabled: true, url: "" });
  assert.deepEqual(queueConfig(QUEUE_ENV), { enabled: true, url: "https://queue.example.invalid/jobs" });
});

test("submit: disabled queue refuses before any transport call", async () => {
  const post = stubQueuePost({ jobId: "q-1" });
  await assert.rejects(
    () => submitQueueJob(buildQueueJob(INPUT), {}, { queuePost: post }),
    (e) => e instanceof QueueError && e.code === "queue_disabled",
  );
  assert.equal(post.calls.length, 0);
});

test("submit: enabled queue without a URL refuses as not configured", async () => {
  const post = stubQueuePost({ jobId: "q-1" });
  await assert.rejects(
    () => submitQueueJob(buildQueueJob(INPUT), { TRIO_QUEUE_ENABLED: "1" }, { queuePost: post }),
    (e) => e instanceof QueueError && e.code === "queue_not_configured",
  );
  assert.equal(post.calls.length, 0);
});

test("submit: posts the envelope to the configured URL and echoes the filed job id", async () => {
  const job = buildQueueJob(INPUT);
  const post = stubQueuePost({ jobId: "filed-42" });
  const result = await submitQueueJob(job, QUEUE_ENV, { queuePost: post });
  assert.deepEqual(result, { jobId: "filed-42" });
  assert.equal(post.calls.length, 1);
  assert.equal(post.calls[0].url, "https://queue.example.invalid/jobs");
  assert.deepEqual(post.calls[0].job, job);
});

test("submit: a malformed job, a throwing transport, or a missing job id all fail as queue_submit_failed", async () => {
  const job = buildQueueJob(INPUT);
  await assert.rejects(
    () => submitQueueJob({ ...job, image: null }, QUEUE_ENV, { queuePost: stubQueuePost({ jobId: "q-1" }) }),
    (e) => e instanceof QueueError && e.code === "queue_submit_failed",
  );
  await assert.rejects(
    () => submitQueueJob(job, QUEUE_ENV, { queuePost: stubQueuePost(new Error("down")) }),
    (e) => e instanceof QueueError && e.code === "queue_submit_failed",
  );
  await assert.rejects(
    () => submitQueueJob(job, QUEUE_ENV, { queuePost: stubQueuePost({}) }),
    (e) => e instanceof QueueError && e.code === "queue_submit_failed",
  );
  await assert.rejects(
    () => submitQueueJob(job, QUEUE_ENV, {}),
    (e) => e instanceof QueueError && e.code === "queue_submit_failed",
  );
});
