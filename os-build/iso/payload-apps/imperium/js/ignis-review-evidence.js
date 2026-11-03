// IGNIS-ONEOFONE-17 (Del's one-of-one bar, Oct 30): the Ignis
// review queue by evidence completeness, in honest form. It counts
// only what the session log actually recorded: the recorded ok
// Ignis assessments already awaiting human review
// (requires_human_review === true, the ONEOFONE-3 queue),
// bucketed by whether their observations carry evidence a human
// reviewer can actually inspect — the same completeness read
// ONEOFONE-4 applies to all successful Ignis assessments, here
// scoped to the flagged queue. A duty officer opening the queue
// can see at a glance how much of the flagged work is actually
// inspectable — fully evidenced, partially evidenced, or with
// nothing to inspect — without this panel ever judging whether
// the evidence is good, re-scoring anything, or claiming a
// flagged assessment is correct because its evidence field is
// filled in. Fully evidenced means every observation carries a
// non-empty evidence string; partially evidenced means some but
// not all do; unevidenced means no observation carries one (an
// empty observations array counts here — a flagged assessment
// with nothing to inspect); unassessable means the entry carries
// no usable observations array at all — a restored or hand-built
// entry the panel refuses to guess about, never a silent
// unevidenced. Per the v2 contract (js/schema.js) observations
// live on the response itself; the assessment-nested fallback
// covers entries shaped like the ONEOFONE-2 test fixtures, which
// nest observations under assessment, exactly as ONEOFONE-4 and
// ONEOFONE-16 do. Clear and unknown-flag entries are not
// awaiting review and move no bucket, failures contribute
// nothing (a failed request produced no assessment), other
// products' entries move no bucket, and an empty or held
// session reads all zeros rather than inventing a queue.
//
// Pure read over log entries: no sampling, no model, no live calls.

export function ignisReviewByEvidence(entries) {
  const counts = {
    totalFlagged: 0,
    fullyEvidenced: 0,
    partiallyEvidenced: 0,
    unevidenced: 0,
    unassessable: 0,
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
    counts.totalFlagged += 1;
    const response = entry.response;
    const observations = Array.isArray(response?.observations)
      ? response.observations
      : response?.assessment?.observations;
    if (!Array.isArray(observations)) {
      counts.unassessable += 1;
      continue;
    }
    let evidenced = 0;
    for (const obs of observations) {
      if (typeof obs?.evidence === "string" && obs.evidence.trim().length > 0) {
        evidenced += 1;
      }
    }
    if (observations.length > 0 && evidenced === observations.length) {
      counts.fullyEvidenced += 1;
    } else if (evidenced > 0) {
      counts.partiallyEvidenced += 1;
    } else {
      counts.unevidenced += 1;
    }
  }
  return counts;
}
