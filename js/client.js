// Analysis client: POSTs one sampled frame to the assessment endpoint and
// validates the response against the contract in schema.js. Every failure
// mode (network, HTTP status, unparseable body, schema violation) throws an
// AssessError with a `kind`, so the UI can show the real error and never
// render a fabricated assessment.

import { validateAssessment } from "./schema.js";

export class AssessError extends Error {
  constructor(kind, message) {
    super(message);
    this.name = "AssessError";
    this.kind = kind; // "network" | "http" | "invalid"
  }
}

// payload: { timestamp: string (ISO-8601), image: string (JPEG data URL) }
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
    throw new AssessError("http", `Endpoint returned HTTP ${res.status}${res.statusText ? " " + res.statusText : ""}`);
  }

  let body;
  try {
    body = await res.json();
  } catch (err) {
    throw new AssessError("invalid", `Endpoint response was not valid JSON: ${err && err.message ? err.message : String(err)}`);
  }

  const result = validateAssessment(body);
  if (!result.ok) {
    throw new AssessError("invalid", `Endpoint response failed schema validation: ${result.errors.join("; ")}`);
  }
  return result.value;
}
