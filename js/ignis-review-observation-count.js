// IGNIS-ONEOFONE-19 (Del's one-of-one bar, Oct 30): the Ignis
// review queue by observation count, in honest form. It counts
// only what the session log actually recorded: the recorded ok
// Ignis assessments already awaiting human review
// (requires_human_review === true, the ONEOFONE-3 queue),
// bucketed by how many observations the response itself
// recorded — the same observations read ONEOFONE-16 buckets by
// category and ONEOFONE-17 reads for evidence, here counted
// rather than classified. A duty officer opening the queue can
// see at a glance how much of the flagged work rests on a
// single observation versus a fuller recorded picture, without
// this panel ever judging whether the observations are good,
// re-scoring anything, or claiming a many-observation flagged
// assessment is reliable because it listed more. No
// observations means the response recorded an empty array —
// the assessment stated nothing it saw; one means exactly one;
// two or three means two or three; four or more means four or
// more; unrecorded means no usable observations array at all —
// a restored or hand-built entry the panel refuses to guess
// about, never a silent zero. Clear and unknown-flag entries
// are not awaiting review and move no bucket, failures
// contribute nothing (a failed request produced no assessment),
// other products' entries move no bucket, and an empty or held
// session reads all zeros rather than inventing a queue.
//
// Pure read over log entries: no sampling, no model, no live calls.

export function ignisReviewByObservationCount(entries) {
  const counts = {
    totalFlagged: 0,
    none: 0,
    one: 0,
    twoOrThree: 0,
    fourOrMore: 0,
    unrecorded: 0,
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
      counts.unrecorded += 1;
    } else if (observations.length === 0) {
      counts.none += 1;
    } else if (observations.length === 1) {
      counts.one += 1;
    } else if (observations.length <= 3) {
      counts.twoOrThree += 1;
    } else {
      counts.fourOrMore += 1;
    }
  }
  return counts;
}
