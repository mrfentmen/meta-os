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
