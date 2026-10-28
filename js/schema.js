// Validation for the Meta Sentinel event-assessment contract (BRIEF.md section 5, Agent 2).
// Pure function, no DOM access: safe to import from browser and from node tests.
//
// Contract:
// {
//   "timestamp": "ISO-8601 timestamp",
//   "observations": [{ "action": string, "evidence": string, "confidence": 0.0..1.0 }],
//   "event_type": "event category or unknown",
//   "assessment": "brief explanation",
//   "uncertainty": "what cannot be determined from the evidence",
//   "requires_human_review": true|false
// }

function isPlainObject(v) {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}

function isNonEmptyString(v) {
  return typeof v === "string" && v.trim().length > 0;
}

export function validateAssessment(value) {
  const errors = [];

  if (!isPlainObject(value)) {
    return { ok: false, errors: ["response is not a JSON object"] };
  }

  if (!isNonEmptyString(value.timestamp)) {
    errors.push("timestamp: missing or not a string");
  } else if (Number.isNaN(Date.parse(value.timestamp))) {
    errors.push("timestamp: not a parseable ISO-8601 date");
  }

  if (!Array.isArray(value.observations)) {
    errors.push("observations: missing or not an array");
  } else {
    value.observations.forEach((obs, i) => {
      if (!isPlainObject(obs)) {
        errors.push(`observations[${i}]: not an object`);
        return;
      }
      if (!isNonEmptyString(obs.action)) {
        errors.push(`observations[${i}].action: missing or not a non-empty string`);
      }
      if (typeof obs.evidence !== "string") {
        errors.push(`observations[${i}].evidence: missing or not a string`);
      }
      if (typeof obs.confidence !== "number" || Number.isNaN(obs.confidence)) {
        errors.push(`observations[${i}].confidence: missing or not a number`);
      } else if (obs.confidence < 0 || obs.confidence > 1) {
        errors.push(`observations[${i}].confidence: out of range 0..1`);
      }
    });
  }

  if (!isNonEmptyString(value.event_type)) {
    errors.push("event_type: missing or not a non-empty string");
  }
  if (typeof value.assessment !== "string") {
    errors.push("assessment: missing or not a string");
  }
  if (typeof value.uncertainty !== "string") {
    errors.push("uncertainty: missing or not a string");
  }
  if (typeof value.requires_human_review !== "boolean") {
    errors.push("requires_human_review: missing or not a boolean");
  }

  if (errors.length > 0) {
    return { ok: false, errors };
  }
  return { ok: true, value, errors: [] };
}
