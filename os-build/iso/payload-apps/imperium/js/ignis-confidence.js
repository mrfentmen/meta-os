// IGNIS-ONEOFONE-2 (Del's one-of-one bar, Oct 29): the Ignis
// reported-confidence spread. This is the calibrated-uncertainty
// item in honest form: it does not collapse assessments to alarm /
// no-alarm, it shows the confidence values the recorded assessments
// themselves reported on their observations, banded high (>= 0.8),
// medium (>= 0.5), low (below 0.5), or unreported (null, missing, or
// not a finite number — the contract allows confidence: null).
// Pure read over log entries: no sampling, no model, no live calls.
// Only ok Ignis entries move a bucket: a failed request produced no
// assessment, other products' entries move no bucket, and an ok entry
// with no observations array contributes nothing. An empty or held
// session reads all zeros rather than inventing a reading. Bands are
// a display grouping of reported values, not a calibration claim:
// nothing here re-scores, re-weights, or thresholds an assessment
// into a decision.

export function ignisReportedConfidence(entries) {
  const counts = {
    total: 0,
    high: 0,
    medium: 0,
    low: 0,
    unreported: 0,
  };
  for (const entry of entries ?? []) {
    if (!entry || entry.status !== "ok" || entry.product !== "ignis") {
      continue;
    }
    const observations = entry.response?.assessment?.observations;
    if (!Array.isArray(observations)) {
      continue;
    }
    for (const obs of observations) {
      const confidence = obs?.confidence;
      counts.total += 1;
      if (typeof confidence !== "number" || !Number.isFinite(confidence)) {
        counts.unreported += 1;
      } else if (confidence >= 0.8) {
        counts.high += 1;
      } else if (confidence >= 0.5) {
        counts.medium += 1;
      } else {
        counts.low += 1;
      }
    }
  }
  return counts;
}
