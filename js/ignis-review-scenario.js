// IGNIS-ONEOFONE-15 (Del's one-of-one bar, Oct 30): the Ignis
// review queue by scenario label, in honest form. It counts only
// what the session log actually recorded: the assessments already
// awaiting human review — recorded ok Ignis assessments whose
// assessment itself carried requires_human_review === true (the
// ONEOFONE-3 queue) — split by the scenario label the operator
// selected (or typed as a custom label) when the request was made,
// the label js/log.js record() stored as scenario_label on each
// entry at submit time (the ONEOFONE-10 field). A duty officer
// opening the queue can see at a glance which staged scenarios the
// flagged work came from — say, steam-or-fog look-alikes
// dominating the queue after a drill — without this panel ever
// re-flagging anything itself. Clear and unknown-flag entries are
// not awaiting review and move no bucket, exactly as in
// ONEOFONE-6's triage; failures contribute nothing (a failed
// request produced no assessment), other products' entries move no
// bucket, and a flagged entry with no usable scenario label (no
// scenario chosen, empty or non-string label, recorded before the
// label existed, restored from an older export) still counts in
// the total and in unlabeled, never guessed into a bucket.
// Scenario labels are open-ended (the operator may type any custom
// label), so buckets live in a byScenario map keyed by the exact
// recorded string; rendering sorts the keys so the panel line is
// stable. An empty or held session reads all zeros rather than
// inventing a queue mix. This panel never judges whether a flag
// was right, only which label the record says each flagged
// assessment carried.
//
// Pure read over log entries: no sampling, no model, no live calls.

export function ignisReviewByScenario(entries) {
  const counts = {
    totalFlagged: 0,
    unlabeled: 0,
    byScenario: {},
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
    const label = entry.scenario_label;
    if (typeof label === "string" && label.length > 0) {
      counts.byScenario[label] = (counts.byScenario[label] ?? 0) + 1;
    } else {
      counts.unlabeled += 1;
    }
  }
  return counts;
}
