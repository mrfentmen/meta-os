// IGNIS-ONEOFONE-20 (Del's one-of-one bar, Oct 30): the Ignis
// review queue by reported latency, in honest form. It counts
// only what the session log actually recorded: the recorded ok
// Ignis assessments already awaiting human review
// (requires_human_review === true, the ONEOFONE-3 queue),
// bucketed by the server-reported processing latency the
// response itself carried (processing.latency_ms, a v2 contract
// field, js/schema.js) — under one second, one to five seconds,
// five seconds or more, or unreported where no usable latency
// value exists to read. A duty officer opening the queue can
// see at a glance whether the flagged work arrived fast or
// waited on the server, without this panel ever judging whether
// a slow flagged assessment is more or less trustworthy, or
// claiming a fast one is reliable because it returned quickly:
// the bands are a display grouping of reported numbers, not a
// speed or quality claim, and latency here is server-reported,
// never measured by this panel. Unreported means the latency
// value is null (the contract allows it), missing, not a finite
// number, or negative — a restored or hand-built entry the panel
// refuses to guess about, never a silent zero. Clear and
// unknown-flag entries are not awaiting review and move no
// bucket, failures contribute nothing (a failed request produced
// no assessment), other products' entries move no bucket, and an
// empty or held session reads all zeros rather than inventing a
// queue.
//
// Pure read over log entries: no sampling, no model, no live calls.

export function ignisReviewByLatency(entries) {
  const counts = {
    totalFlagged: 0,
    under1s: 0,
    oneTo5s: 0,
    fiveOrMore: 0,
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
    counts.totalFlagged += 1;
    const latencyMs = entry.response?.processing?.latency_ms;
    if (typeof latencyMs !== "number" || !Number.isFinite(latencyMs) || latencyMs < 0) {
      counts.unreported += 1;
    } else if (latencyMs < 1000) {
      counts.under1s += 1;
    } else if (latencyMs < 5000) {
      counts.oneTo5s += 1;
    } else {
      counts.fiveOrMore += 1;
    }
  }
  return counts;
}
