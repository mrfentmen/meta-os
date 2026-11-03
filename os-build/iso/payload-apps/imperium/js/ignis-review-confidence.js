// IGNIS-ONEOFONE-14 (Del's one-of-one bar, Oct 30): the Ignis
// review queue by reported confidence. The label-feedback slice
// this number was first slated for is blocked: no officer
// disposition, verdict, or label-feedback field exists anywhere
// in the session log or the v2 contract (log entries carry
// request_timestamp, product, status, response, scenario_label,
// and source; assessments carry category, summary, uncertainty,
// requires_human_review, observations, and processing) — so there
// is no recorded disposition to bucket by, and this panel invents
// none. What the log does record for every flagged item is the
// confidence each of its observations itself reported, so this
// panel reads that instead: the observations on recorded ok Ignis
// assessments already awaiting human review (requires_human_review
// === true, the ONEOFONE-3 queue), banded with ONEOFONE-2's bands
// — high (>= 0.8), medium (>= 0.5), low (below 0.5), or unreported
// (null, missing, or not a finite number — the contract allows
// confidence: null). A duty officer opening the queue sees whether
// the flagged work rests on high reported confidence or on thin
// readings, without this panel ever re-scoring anything: bands
// are a display grouping of reported values, not a calibration
// claim, and never a judgment on whether a flag was right. Clear
// and unknown-flag entries are not awaiting review and move no
// bucket, failures contribute nothing (a failed request produced
// no assessment), other products' entries move no bucket, a
// flagged entry with no observations array contributes nothing,
// and an empty or held session reads all zeros rather than
// inventing a queue.
//
// Pure read over log entries: no sampling, no model, no live calls.

export function ignisReviewByConfidence(entries) {
  const counts = {
    total: 0,
    high: 0,
    medium: 0,
    low: 0,
    unreported: 0,
  };
  for (const entry of entries ?? []) {
    if (
      !entry ||
      entry.status !== "ok" ||
      entry.product !== "ignis" ||
      entry.response?.assessment?.requires_human_review !== true
    ) {
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
