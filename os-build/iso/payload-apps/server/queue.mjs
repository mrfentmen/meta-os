// OS queue transport, Trio side (Rowan's lane) — steps 1-3: the job
// envelope, the submit adapter, the result-fetch adapter, the poll
// loop, and the production HTTP transports, wired into /api/assess
// by server/assess.mjs with the direct Spark path as fallback.
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
//   - submitQueueJob() posts that envelope to the queue service
//     through an injected queuePost (tests inject a stub; production
//     uses httpQueuePost below). It refuses in layers, like the model
//     adapter: queue disabled, queue URL not configured, bad job,
//     submit failure — every refusal is a typed QueueError, never a
//     fabricated job id or assessment.
//   - fetchQueueResult() reads one result envelope for a filed job
//     id through an injected queueGet (tests inject a stub;
//     production uses httpQueueGet below). The result shape is the one
//     Pax settled 2026-10-30 (room-1 ruling, index 423): the result
//     body is { job_id, status: "ok" | "failed", assessment:
//     <v2 contract object> | null, error: string | null, model,
//     latency_ms, completed_at }, keyed {job_ns}:{jid}:result with
//     job_ns "trio" on the OS side; an ok result carries ONLY an
//     assessment that already passed validateAssessment on the agent
//     side — invalid model output is status failed, never a written
//     assessment. This reader ALSO still accepts the step-2 proposed
//     shape (version 1, kind "trio-assessment-result", jobId,
//     status "pending" | "done" | "failed") and normalizes both to
//     { status: "pending" | "done" | "failed", jobId, ... }, so a
//     resident agent still emitting the proposed shape is not
//     rejected mid-transition; a "pending" status is accepted in
//     either shape (the HTTP front may also answer 404 before a
//     result exists, which httpQueueGet maps to pending). A done
//     envelope carries the resident agent's assessment verbatim —
//     this module does NOT validate it; assess.mjs runs it through
//     validateAssessment before /api/assess ever sends it, exactly
//     as the model path does. A failed envelope carries the agent's
//     error string when it has one. Anything malformed is a fetch
//     failure, never a fabricated assessment. The Trio job is NOT
//     forced into the OS spark-complete envelope — that one is for
//     OS-internal text jobs and has no frame or contract typing.
//   - pollQueueResult() repeats fetchQueueResult until done/failed
//     or a bounded attempt count is exhausted; a timeout is a typed
//     QueueError, and assess.mjs then falls back to the direct Spark
//     path and logs the fallback — never a faked contract field.
//   - httpQueuePost()/httpQueueGet() are the production transports
//     for the thin HTTP front Pax described (POST /jobs to submit,
//     GET /jobs/:id/result to poll, on the service behind
//     TRIO_QUEUE_URL as its base URL). They are the only place a
//     queue HTTP call leaves this server.
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
    this.code = code; // "queue_disabled" | "queue_not_configured" | "queue_submit_failed" | "queue_fetch_failed"
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

export const QUEUE_RESULT_VERSION = 1;
export const QUEUE_RESULT_KIND = "trio-assessment-result";

// Bounded poll defaults (Pax ruling: "server polls with a bounded
// timeout"). 30 attempts x 1s is the default bound; tests inject a
// stub sleep and smaller counts, so no test ever waits real seconds.
export const QUEUE_POLL_INTERVAL_MS = 1000;
export const QUEUE_POLL_MAX_ATTEMPTS = 30;

function isPlainObject(v) {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}

// Normalizes one raw result envelope to the internal shape, or throws
// via fail(). Accepts the Pax-agreed shape and the step-2 proposed
// shape (see the header); anything else is malformed.
function parseQueueResultEnvelope(result, jobId, fail) {
  if (!isPlainObject(result)) fail("result is not an object");
  // A job id carried in either field name must match the request.
  if (result.job_id !== undefined && result.job_id !== jobId) fail("job_id does not match the requested job");
  if (result.jobId !== undefined && result.jobId !== jobId) fail("jobId does not match the requested job");
  const passthrough = {};
  if (result.model !== undefined) {
    if (typeof result.model !== "string" && result.model !== null) fail("model is not a string");
    passthrough.model = result.model;
  }
  if (result.latency_ms !== undefined) {
    if (typeof result.latency_ms !== "number" && result.latency_ms !== null) fail("latency_ms is not a number");
    passthrough.latency_ms = result.latency_ms;
  }
  if (result.completed_at !== undefined) {
    if (typeof result.completed_at !== "string") fail("completed_at is not a string");
    passthrough.completed_at = result.completed_at;
  }
  // Proposed step-2 shape: version/kind present means it must be exact.
  if (result.version !== undefined || result.kind !== undefined) {
    if (result.version !== QUEUE_RESULT_VERSION) fail(`version is not ${QUEUE_RESULT_VERSION}`);
    if (result.kind !== QUEUE_RESULT_KIND) fail(`kind is not "${QUEUE_RESULT_KIND}"`);
    if (result.jobId !== jobId) fail("jobId does not match the requested job");
    if (result.status === "pending") return { status: "pending", jobId };
    if (result.status === "done") {
      if (!isPlainObject(result.assessment)) fail("done result carries no assessment object");
      return { status: "done", jobId, assessment: result.assessment, ...passthrough };
    }
    if (result.status === "failed") {
      if (result.error !== undefined && typeof result.error !== "string") fail("failed result carries a non-string error");
      return result.error === undefined
        ? { status: "failed", jobId, ...passthrough }
        : { status: "failed", jobId, error: result.error, ...passthrough };
    }
    fail(`unknown status "${result.status}"`);
  }
  // Pax-agreed shape: job_id + status ok|failed (pending accepted too,
  // for a front that answers pending explicitly rather than 404).
  if (result.job_id !== jobId) fail("job_id does not match the requested job");
  if (result.status === "pending") {
    if (result.assessment !== undefined && result.assessment !== null) fail("pending result carries an assessment");
    return { status: "pending", jobId, ...passthrough };
  }
  if (result.status === "ok") {
    if (!isPlainObject(result.assessment)) fail("ok result carries no assessment object");
    if (result.error !== undefined && result.error !== null) fail("ok result carries an error");
    return { status: "done", jobId, assessment: result.assessment, ...passthrough };
  }
  if (result.status === "failed") {
    if (result.error !== undefined && result.error !== null && typeof result.error !== "string") {
      fail("failed result carries a non-string error");
    }
    if (result.assessment !== undefined && result.assessment !== null) fail("failed result carries an assessment");
    const out = { status: "failed", jobId, ...passthrough };
    if (typeof result.error === "string") out.error = result.error;
    return out;
  }
  fail(`unknown status "${result.status}"`);
}

// Fetches one result envelope for a filed job id. deps.queueGet is
// the transport (url, jobId) => result envelope or a promise of one;
// tests inject a stub, so no test ever touches a real queue. Returns
// the normalized shape (see parseQueueResultEnvelope):
//   { status: "pending", jobId } — claimed or unanswered so far
//   { status: "done", jobId, assessment } — verbatim, NOT validated
//     here; assess.mjs must validate it before it is sent
//   { status: "failed", jobId, error? } — the agent's error string
// Refusals and malformed envelopes are typed QueueErrors, never a
// fabricated assessment: a job id mismatch, a wrong version/kind, an
// unknown status, or an ok/done envelope without an assessment
// object all fail as queue_fetch_failed.
export async function fetchQueueResult(jobId, env = process.env, deps = {}) {
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
  if (typeof jobId !== "string" || jobId.length === 0) {
    throw new QueueError("queue_fetch_failed", "Cannot fetch a queue result without a job id.");
  }
  const queueGet = deps.queueGet;
  if (typeof queueGet !== "function") {
    throw new QueueError("queue_fetch_failed", "No queue transport is wired for the queue result fetch.");
  }
  let result;
  try {
    result = await queueGet(cfg.url, jobId);
  } catch (err) {
    if (err instanceof QueueError) throw err;
    throw new QueueError(
      "queue_fetch_failed",
      `Queue result fetch failed: ${err && err.message ? err.message : String(err)}`,
    );
  }
  const fail = (detail) => {
    throw new QueueError("queue_fetch_failed", `Queue result envelope malformed: ${detail}`);
  };
  return parseQueueResultEnvelope(result, jobId, fail);
}

// Polls one filed job until its result is done/failed or the bound
// is exhausted. deps passes through to fetchQueueResult (queueGet),
// plus pollIntervalMs, maxAttempts, and sleep (all injectable for
// tests, so no test waits real time). A pending streak that exhausts
// the bound throws queue_fetch_failed — the caller (assess.mjs)
// falls back to the direct Spark path and logs it. Disabled,
// not-configured, and transport errors propagate immediately rather
// than looping, because they are not "still pending".
export async function pollQueueResult(jobId, env = process.env, deps = {}) {
  const maxAttempts = deps.maxAttempts ?? QUEUE_POLL_MAX_ATTEMPTS;
  const intervalMs = deps.pollIntervalMs ?? QUEUE_POLL_INTERVAL_MS;
  const sleep = deps.sleep ?? ((ms) => new Promise((resolve) => setTimeout(resolve, ms)));
  for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
    const result = await fetchQueueResult(jobId, env, deps);
    if (result.status !== "pending") return result;
    if (attempt === maxAttempts) break;
    await sleep(intervalMs);
  }
  throw new QueueError(
    "queue_fetch_failed",
    `Queue result poll timed out after ${maxAttempts} attempts: job ${jobId} still pending. The direct Spark path remains the fallback.`,
  );
}

function queueServiceBase(url) {
  return String(url).replace(/\/+$/, "");
}

// Production transports for the thin HTTP front Pax described:
// TRIO_QUEUE_URL is the service base URL (not a /jobs suffix — the
// transports append the paths). deps.fetch injects the transport for
// tests; production uses the global fetch. No test fires a live call.
export async function httpQueuePost(url, job, deps = {}) {
  const fetchFn = deps.fetch ?? globalThis.fetch;
  if (typeof fetchFn !== "function") {
    throw new QueueError("queue_submit_failed", "No fetch implementation is available for the queue submit.");
  }
  let res;
  try {
    res = await fetchFn(`${queueServiceBase(url)}/jobs`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(job),
    });
  } catch (err) {
    throw new QueueError(
      "queue_submit_failed",
      `Queue submit failed: ${err && err.message ? err.message : String(err)}`,
    );
  }
  if (!res.ok) {
    throw new QueueError("queue_submit_failed", `Queue submit failed with HTTP ${res.status}.`);
  }
  let data;
  try {
    data = await res.json();
  } catch {
    throw new QueueError("queue_submit_failed", "Queue submit response was not JSON.");
  }
  const jobId = data && (data.jobId ?? data.id ?? data.job_id);
  if (typeof jobId !== "string" || jobId.length === 0) {
    throw new QueueError("queue_submit_failed", "Queue submit returned no job id.");
  }
  return { jobId };
}

export async function httpQueueGet(url, jobId, deps = {}) {
  const fetchFn = deps.fetch ?? globalThis.fetch;
  if (typeof fetchFn !== "function") {
    throw new QueueError("queue_fetch_failed", "No fetch implementation is available for the queue result fetch.");
  }
  let res;
  try {
    res = await fetchFn(`${queueServiceBase(url)}/jobs/${encodeURIComponent(jobId)}/result`, {
      method: "GET",
    });
  } catch (err) {
    throw new QueueError(
      "queue_fetch_failed",
      `Queue result fetch failed: ${err && err.message ? err.message : String(err)}`,
    );
  }
  // No result key yet on the OS side: the front answers 404, and a
  // missing result is "pending", not a malformed envelope.
  if (res.status === 404) {
    return { job_id: jobId, status: "pending", assessment: null, error: null };
  }
  if (!res.ok) {
    throw new QueueError("queue_fetch_failed", `Queue result fetch failed with HTTP ${res.status}.`);
  }
  try {
    return await res.json();
  } catch {
    throw new QueueError("queue_fetch_failed", "Queue result response was not JSON.");
  }
}
