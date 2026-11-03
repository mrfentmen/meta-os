// IGNIS-ONEOFONE-21 (Del's one-of-one bar, Oct 30): the Ignis
// review queue by summary completeness, in honest form. It counts
// only what the session log actually recorded: the recorded ok
// Ignis assessments already awaiting human review
// (requires_human_review === true, the ONEOFONE-3 queue),
// bucketed by whether the assessment itself carries a summary a
// duty officer can actually read — the assessment.summary string
// the v2 contract requires (js/schema.js: a string, which may be
// empty). A duty officer opening the queue can see at a glance
// how much of the flagged work arrives with something to read
// versus a blank or missing summary, without this panel ever
// judging whether a summary is accurate, re-scoring anything, or
// claiming a flagged assessment with a summary is reliable
// because it wrote one down. With summary means a string with
// non-whitespace content; empty summary means a string that is
// empty or whitespace only — the assessment stated nothing to
// read; unrecorded means no usable summary string at all — a
// missing, null, or non-string value on a restored or hand-built
// entry the panel refuses to guess about, never a silent empty.
// Clear and unknown-flag entries are not awaiting review and
// move no bucket, failures contribute nothing (a failed request
// produced no assessment), other products' entries move no
// bucket, and an empty or held session reads all zeros rather
// than inventing a queue.
//
// Pure read over log entries: no sampling, no model, no live calls.

export function ignisReviewBySummary(entries) {
  const counts = {
    totalFlagged: 0,
    withSummary: 0,
    emptySummary: 0,
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
    const summary = entry.response?.assessment?.summary;
    if (typeof summary !== "string") {
      counts.unrecorded += 1;
    } else if (summary.trim().length > 0) {
      counts.withSummary += 1;
    } else {
      counts.emptySummary += 1;
    }
  }
  return counts;
}
