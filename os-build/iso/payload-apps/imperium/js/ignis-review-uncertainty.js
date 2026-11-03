// IGNIS-ONEOFONE-18 (Del's one-of-one bar, Oct 30): the Ignis
// review queue by uncertainty disclosure, in honest form. It counts
// only what the session log actually recorded: the recorded ok
// Ignis assessments already awaiting human review
// (requires_human_review === true, the ONEOFONE-3 queue),
// bucketed by whether the assessment itself disclosed caveats —
// the same disclosure read ONEOFONE-5 applies to all successful
// Ignis assessments, here scoped to the flagged queue. A duty
// officer opening the queue can see at a glance how much of the
// flagged work arrived with its own caveats attached — disclosed,
// none disclosed, or unrecorded where no usable uncertainty array
// exists to read — without this panel ever judging whether the
// caveats are sufficient, re-scoring anything, or claiming a
// flagged assessment is reliable because it disclosed nothing.
// Disclosed means the assessment carries a non-empty uncertainty
// array (the v2 contract's own caveat list, read on the same
// path the history renders: response.assessment.uncertainty);
// none disclosed means an empty array — the assessment stated no
// caveats; unrecorded means no usable uncertainty array at all —
// a restored or hand-built entry the panel refuses to guess
// about, never a silent "none". Clear and unknown-flag entries
// are not awaiting review and move no bucket, failures
// contribute nothing (a failed request produced no assessment),
// other products' entries move no bucket, and an empty or held
// session reads all zeros rather than inventing a queue.
//
// Pure read over log entries: no sampling, no model, no live calls.

export function ignisReviewByUncertainty(entries) {
  const counts = {
    totalFlagged: 0,
    disclosed: 0,
    noneDisclosed: 0,
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
    const uncertainty = entry.response.assessment.uncertainty;
    if (!Array.isArray(uncertainty)) {
      counts.unrecorded += 1;
    } else if (uncertainty.length > 0) {
      counts.disclosed += 1;
    } else {
      counts.noneDisclosed += 1;
    }
  }
  return counts;
}
