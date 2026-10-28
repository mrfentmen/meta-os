// Analysis client: POSTs one sampled frame to the assessment endpoint and
// validates the response against the v2 contract in schema.js, mirroring
// native/Sources/MetaTrio/Services/AssessClient.swift. Every failure mode
// (network, HTTP status, server error body, unparseable body, schema
// violation) throws an AssessError with a `kind`, so the UI can show the
// real error and never render a fabricated assessment.

import { validateAssessment } from "./schema.js";

export class AssessError extends Error {
  constructor(kind, message) {
    super(message);
    this.name = "AssessError";
    this.kind = kind; // "network" | "http" | "invalid"
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
