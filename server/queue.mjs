// OS queue transport, Trio side (Rowan's lane) — step 1: the job
// envelope and the submit adapter. NOT yet wired into /api/assess.
//
// Del's direction, 2026-10-30 (relayed by Pax): the OS operates the
// Trio — one submission, Best Agentic aim. The Trio server submits
// assessments as jobs to the OS job queue; a resident agent claims and
// answers them with Spark; the SPARK-TRANSPORT-1 direct path stays as
// fallback; apps keep calling /api/assess unchanged. Hard cutoff Nov 2:
// the queue round trip is verified live by then, or the clean Trio
// ships alone.
//
// What this module does and does not do, honestly:
//   - buildQueueJob() turns a validated assess input (the same shape
//     server/assess.mjs validates) into a versioned job envelope the
//     resident agent can claim: product, timestamp, and the frame
//     itself as the same JPEG data URL the clients already send, plus
//     a byte length, a SHA-256 of the frame bytes, and a deterministic
//     id derived from product + timestamp + frame bytes (so a
//     resubmitted frame is the same job, and the duty-officer audit
//     trail can name it). No assessment is invented here: a job is a
//     submission, not an answer.
//   - submitQueueJob() posts that envelope to the queue URL the
//     operator configured, through an injected queuePost (tests inject
//     a stub; production wiring is the next step). It refuses in
//     layers, like the model adapter: queue disabled, queue URL not
//     configured, bad job, submit failure — every refusal is a typed
//     QueueError, never a fabricated job id or assessment.
//   - What is deliberately NOT here yet: wiring into handleAssess,
//     and the claim/result poll. A submit returns a job id, not an
//     assessment, and /api/assess must still return a v2 assessment
//     object — so the result-retrieval shape is agreed with Pax's
//     resident-agent end before anything is wired in. Until then the
//     direct Spark path remains the only live path, and this module
//     changes no request behaviour.
//   - The queue service itself is a named external service, never
//     inside this repo: its URL comes only from the TRIO_QUEUE_URL
//     environment variable, server-side, and no key material is ever
//     put in a job envelope, a commit, or a log.

import { createHash } from "node:crypto";

import { isProductId } from "../js/products.js";

export class QueueError extends Error {
  constructor(code, message) {
    super(message);
    this.name = "QueueError";
    this.code = code; // "queue_disabled" | "queue_not_configured" | "queue_submit_failed"
  }
}

export const QUEUE_JOB_VERSION = 1;
export const QUEUE_JOB_KIND = "trio-assessment";

export function queueConfig(env = process.env) {
  return {
    enabled: env.TRIO_QUEUE_ENABLED === "1",
    url: typeof env.TRIO_QUEUE_URL === "string" ? env.TRIO_QUEUE_URL : "",
  };
}

function sha256Hex(bytes) {
  return createHash("sha256").update(bytes).digest("hex");
}

// input: the validated assess input { product, timestamp, imageBytes
// (Buffer), mediaType }. Throws QueueError("queue_submit_failed") on a
// bad input rather than building a job from garbage.
export function buildQueueJob(input) {
  if (!input || typeof input !== "object") {
    throw new QueueError("queue_submit_failed", "Cannot build a queue job from a missing assess input.");
  }
  if (!isProductId(input.product)) {
    throw new QueueError("queue_submit_failed", `Cannot build a queue job for product "${input.product}".`);
  }
  if (typeof input.timestamp !== "string" || input.timestamp.length === 0) {
    throw new QueueError("queue_submit_failed", "Cannot build a queue job without a timestamp.");
  }
  let bytes;
  try {
    bytes = Buffer.from(input.imageBytes);
  } catch {
    throw new QueueError("queue_submit_failed", "Cannot build a queue job without image bytes.");
  }
  if (bytes.length === 0) {
    throw new QueueError("queue_submit_failed", "Cannot build a queue job without image bytes.");
  }
  // assess.mjs only ever validates JPEG frames, so the job's media
  // type is fixed; a non-JPEG input never reaches this builder.
  const mediaType = "image/jpeg";
  const digest = sha256Hex(bytes);
  const id = `trio-${sha256Hex(Buffer.concat([
    Buffer.from(`${input.product}\0${input.timestamp}\0`, "utf8"),
    bytes,
  ])).slice(0, 32)}`;
  return {
    version: QUEUE_JOB_VERSION,
    kind: QUEUE_JOB_KIND,
    id,
    product: input.product,
    timestamp: input.timestamp,
    image: {
      mediaType,
      byteLength: bytes.length,
      sha256: digest,
      dataUrl: `data:image/jpeg;base64,${bytes.toString("base64")}`,
    },
  };
}

function isUsableJob(job) {
  return (
    job &&
    typeof job === "object" &&
    job.version === QUEUE_JOB_VERSION &&
    job.kind === QUEUE_JOB_KIND &&
    typeof job.id === "string" &&
    job.id.length > 0 &&
    isProductId(job.product) &&
    typeof job.timestamp === "string" &&
    job.timestamp.length > 0 &&
    job.image &&
    typeof job.image === "object" &&
    typeof job.image.dataUrl === "string" &&
    job.image.dataUrl.startsWith("data:image/jpeg;base64,")
  );
}

// Posts one envelope and returns its job id. deps.queuePost is the
// transport (url, job) => { jobId } or a promise of one; tests inject
// a stub, so no test ever touches a real queue. The queue service
// answers with the id it filed the job under — that id is echoed, not
// invented: a missing or non-string jobId is a submit failure.
export async function submitQueueJob(job, env = process.env, deps = {}) {
  const cfg = queueConfig(env);
  if (!cfg.enabled) {
    throw new QueueError(
      "queue_disabled",
      "The OS queue path is disabled: TRIO_QUEUE_ENABLED is not 1. The direct Spark path remains the fallback.",
    );
  }
  if (!cfg.url) {
    throw new QueueError(
      "queue_not_configured",
      "No queue URL is configured on the server. Set TRIO_QUEUE_URL in the server environment.",
    );
  }
  if (!isUsableJob(job)) {
    throw new QueueError("queue_submit_failed", "Refused to submit a malformed queue job.");
  }
  const queuePost = deps.queuePost;
  if (typeof queuePost !== "function") {
    throw new QueueError("queue_submit_failed", "No queue transport is wired for the queue submit.");
  }
  let result;
  try {
    result = await queuePost(cfg.url, job);
  } catch (err) {
    if (err instanceof QueueError) throw err;
    throw new QueueError(
      "queue_submit_failed",
      `Queue submit failed: ${err && err.message ? err.message : String(err)}`,
    );
  }
  const jobId = result && result.jobId;
  if (typeof jobId !== "string" || jobId.length === 0) {
    throw new QueueError("queue_submit_failed", "Queue submit returned no job id.");
  }
  return { jobId };
}
