// Hands-Free C7 — the failure voice (R11-247).
//
// When a service is down, the spoken answer must name the outage. "Something went wrong" is the
// failure mode this file exists to prevent: it hides which part is missing, so the listener
// cannot decide anything. The state words come from the records, not from a guess.
export const STATES = {
  down: "is down",
  degraded: "is running degraded",
  missing: "is missing",
  unknown: "is not answering",
};

export function speakFailure({ service, state, detail = "" } = {}) {
  const name = String(service || "that service").trim();
  const word = STATES[state] || STATES.unknown;
  const line = name + " " + word + ". Orders for " + name + " are not running.";
  return {
    text: detail ? line + " " + detail : line,
    names: { service: name, state: state || "unknown" },
    // A caller must not be able to read this as success.
    ok: false,
  };
}

export function speakSuccess({ count = 0 } = {}) {
  return { text: count === 1 ? "One order ran." : count + " orders ran.", ok: true };
}
