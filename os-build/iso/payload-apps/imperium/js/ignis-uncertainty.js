// IGNIS-ONEOFONE-5 (Del's one-of-one bar, Oct 29): the Ignis
// uncertainty-disclosure panel. It counts only what the session log
// actually recorded: successful Ignis assessments, bucketed by the
// uncertainty items the assessment itself disclosed. Disclosed means
// the assessment carries a non-empty uncertainty array (the v2
// contract's own caveat list, read on the same path the history
// renders: response.assessment.uncertainty); none disclosed means an
// empty array — the assessment stated no caveats; unrecorded means
// no usable uncertainty array at all — a restored or hand-built
// entry the panel refuses to guess about, never a silent "none".
// Failures contribute nothing (a failed request produced no
// assessment), other products' entries move no bucket, and an empty
// or held session reads all zeros rather than inventing candor.
// This counts disclosed strings only: it never judges whether the
// caveats are sufficient, never re-scores an assessment, and never
// claims an assessment is reliable because it disclosed nothing.
//
// Pure read over log entries: no sampling, no model, no live calls.

export function ignisUncertaintyDisclosure(entries) {
  const counts = {
    total: 0,
    disclosed: 0,
    noneDisclosed: 0,
    unrecorded: 0,
  };
  for (const entry of entries ?? []) {
    if (!entry || entry.status !== "ok" || entry.product !== "ignis") {
      continue;
    }
    counts.total += 1;
    const uncertainty = entry.response?.assessment?.uncertainty;
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
