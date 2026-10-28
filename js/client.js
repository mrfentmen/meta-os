// Analysis client: POSTs one sampled frame to the assessment endpoint and
// validates the response against the v2 contract in schema.js, mirroring
// native/Sources/MetaTrio/Services/AssessClient.swift. Every failure mode
// (network, HTTP status, server error body, unparseable body, schema
// violation) throws an AssessError with a `kind`, so the UI can show the
// real error and never render a fabricated assessment.

import { validateAssessment } from "./schema.js";

export class AssessError extends Error {
  constructor(kind, message, options = {}) {
    super(message);
    this.name = "AssessError";
    this.kind = kind; // "network" | "http" | "invalid"
    // True only when no request was attempted at all (the endpoint was
    // rejected before sending). Callers use it to leave measured
    // state alone: there is no round trip to report and no latency
    // to log for a request that never went out.
    this.noRequest = options.noRequest === true;
  }
}

// Native parity (AssessClient.swift, HealthClient.swift): the native
// clients reject an endpoint that is not a valid http(s) URL before
// anything is sent, and report a nil latency for it. The web client
// passed every endpoint straight to fetch, so a mistyped scheme failed
// only when fetch rejected it — and the UI then stamped the
// time-to-reject as a "last round trip" and logged it as a measured
// latency, which it was not. An endpoint with no scheme ("/api/assess",
// the default) is a same-origin relative URL and still goes to fetch,
// exactly as before; only an endpoint that claims a scheme is checked,
// and it must parse as http(s) — "localhost:8080/..." is rejected here
// exactly as the native client rejects it.
function assertHttpEndpoint(endpoint, display = endpoint) {
  const candidate = String(endpoint).trim();
  if (!/^[A-Za-z][A-Za-z0-9+.-]*:/.test(candidate)) return;
  let parsed = null;
  try {
    parsed = new URL(candidate);
  } catch {
    parsed = null;
  }
  if (!parsed || (parsed.protocol !== "http:" && parsed.protocol !== "https:")) {
    throw new AssessError("network", `Endpoint is not a valid http(s) URL: ${display}`, { noRequest: true });
  }
}

function serverErrorMessage(body) {
  if (body && typeof body === "object" && !Array.isArray(body)) {
    if (typeof body.error === "string" && body.error.length > 0) {
      return body.error;
    }
  }
  return null;
}

// The health URL for an assessment endpoint: the same origin and prefix,
// with /api/assess swapped for /api/health. A bare base URL just gains
// the /api/health path. This keeps the check pointed at the server the
// user actually configured, never at a guessed host.
export function healthUrlFor(endpoint) {
  const trimmed = String(endpoint).trim().replace(/\/+$/, "");
  if (trimmed.endsWith("/api/assess")) {
    return `${trimmed.slice(0, -"/api/assess".length)}/api/health`;
  }
  return `${trimmed}/api/health`;
}

function validateHealth(body) {
  if (!body || typeof body !== "object" || Array.isArray(body)) return "health response was not an object";
  if (typeof body.ok !== "boolean") return "health response has no boolean ok field";
  if (typeof body.service !== "string" || body.service.length === 0) return "health response has no service name";
  if (!Array.isArray(body.products) || body.products.some((p) => typeof p !== "string")) {
    return "health response has no products list";
  }
  if (!body.model || typeof body.model !== "object" || Array.isArray(body.model)) {
    return "health response has no model status";
  }
  if (typeof body.model.configured !== "boolean" || typeof body.model.live_enabled !== "boolean") {
    return "health response model status is incomplete";
  }
  return null;
}

// GETs the server's /api/health and returns its parsed body, or throws
// an AssessError with the same kinds as assessFrame. Health reachable
// does NOT mean assessments are available: the model may be held, and
// that state is in the returned body for the UI to say plainly.
export async function checkHealth(endpoint, fetchFn = (url, opts) => fetch(url, opts)) {
  const url = healthUrlFor(endpoint);
  assertHttpEndpoint(url, endpoint);
  let res;
  try {
    res = await fetchFn(url, { method: "GET" });
  } catch (err) {
    throw new AssessError("network", `Health check to ${url} failed: ${err && err.message ? err.message : String(err)}`);
  }

  if (!res.ok) {
    let message = `Health endpoint returned HTTP ${res.status}${res.statusText ? " " + res.statusText : ""}`;
    try {
      const body = await res.json();
      const serverError = serverErrorMessage(body);
      if (serverError) message += `: ${serverError}`;
    } catch {
      // Body is not JSON; the HTTP status alone is the real error.
    }
    throw new AssessError("http", message);
  }

  let body;
  try {
    body = await res.json();
  } catch (err) {
    throw new AssessError("invalid", `Health response was not valid JSON: ${err && err.message ? err.message : String(err)}`);
  }

  const serverError = serverErrorMessage(body);
  if (serverError) {
    throw new AssessError("invalid", `Health endpoint returned an error: ${serverError}`);
  }

  const problem = validateHealth(body);
  if (problem) {
    throw new AssessError("invalid", `Health response failed validation: ${problem}`);
  }
  return body;
}

// payload: { product: "vigiles"|"ignis"|"sanitas", timestamp: string
// (ISO-8601), image: string (JPEG data URL) }
// fetchFn is injectable for tests; defaults to the global fetch.
export async function assessFrame(endpoint, payload, fetchFn = (url, opts) => fetch(url, opts)) {
  assertHttpEndpoint(endpoint);
  let res;
  try {
    res = await fetchFn(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  } catch (err) {
    throw new AssessError("network", `Request to ${endpoint} failed: ${err && err.message ? err.message : String(err)}`);
  }

  if (!res.ok) {
    let message = `Endpoint returned HTTP ${res.status}${res.statusText ? " " + res.statusText : ""}`;
    try {
      const body = await res.json();
      const serverError = serverErrorMessage(body);
      if (serverError) message += `: ${serverError}`;
    } catch {
      // Body is not JSON; the HTTP status alone is the real error.
    }
    throw new AssessError("http", message);
  }

  let body;
  try {
    body = await res.json();
  } catch (err) {
    throw new AssessError("invalid", `Endpoint response was not valid JSON: ${err && err.message ? err.message : String(err)}`);
  }

  // The contract's error shape: HTTP 200 with an {"error": "..."} body.
  const serverError = serverErrorMessage(body);
  if (serverError) {
    throw new AssessError("invalid", `Endpoint returned an error: ${serverError}`);
  }

  const result = validateAssessment(body, payload.product);
  if (!result.ok) {
    throw new AssessError("invalid", `Endpoint response failed schema validation: ${result.errors.join("; ")}`);
  }
  return result.value;
}
