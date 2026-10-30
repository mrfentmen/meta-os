// IGNIS-ONEOFONE-3 (Del's one-of-one bar, Oct 29): the Ignis
// duty-officer review queue. It counts only what the session log
// actually recorded: successful Ignis assessments, bucketed by the
// requires_human_review flag the assessment itself carried (js/schema.js
// validates that flag as a boolean on every assessment). Flagged
// means a human review was requested by the assessment; clear means
// it was explicitly not requested; unknown means the flag is missing
// or not a boolean — a restored or hand-built entry the queue refuses
// to guess about, never a silent clear. Failures contribute nothing
// (a failed request produced no assessment), other products' entries
// move no bucket, and an ok entry with no usable assessment still
// counts in the total and in unknown — the total is the recorded
// Ignis successes, and the named buckets never sum past it. This is
// a reading of recorded flags only: it never flags anything itself,
// never re-scores an assessment, and never notifies anyone —
// reaching out stays a human action. Pure read over log entries:
// no sampling, no model, no live calls. An empty or held session
// reads all zeros rather than inventing a queue.

export function ignisReviewQueue(entries) {
  const counts = {
    total: 0,
    flagged: 0,
    clear: 0,
    unknown: 0,
  };
  for (const entry of entries ?? []) {
    if (!entry || entry.status !== "ok" || entry.product !== "ignis") {
      continue;
    }
    counts.total += 1;
    const flag = entry.response?.assessment?.requires_human_review;
    if (flag === true) {
      counts.flagged += 1;
    } else if (flag === false) {
      counts.clear += 1;
    } else {
      counts.unknown += 1;
    }
  }
  return counts;
}
