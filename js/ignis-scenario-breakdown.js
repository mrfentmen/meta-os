// IGNIS-ONEOFONE-10 (Del's one-of-one bar, Oct 30): the Ignis
// scenario breakdown, in honest form. It counts only what the
// session log actually recorded: the recorded ok Ignis assessments,
// bucketed by the scenario label the operator selected (or typed as
// a custom label) when the request was made — the label js/log.js
// record() stored as scenario_label on each entry at submit time.
// The scenario is ground-truth context the operator supplied, never
// inferred after the fact from the image or the assessment: this
// panel shows which staged scenarios the recorded verdicts came
// from, so a duty officer can see whether the session covered, say,
// steam-or-fog look-alikes or only clear smoke — without this panel
// ever assigning a scenario the log did not record. An assessment
// with no usable scenario label (no scenario chosen, empty or
// non-string label, recorded before the label existed, restored
// from an older export) counts in the total and in unlabeled, never
// guessed into a bucket. Failures contribute nothing (a failed
// request produced no assessment), other products' entries move no
// bucket, and an empty or held session reads all zeros rather than
// inventing a scenario mix. Scenario labels are open-ended (the
// operator may type any custom label), so buckets live in a
// byScenario map keyed by the exact recorded string; rendering
// sorts the keys so the panel line is stable. This panel never
// judges whether a scenario label was right, only which label the
// record says each assessment carried.
//
// Pure read over log entries: no sampling, no model, no live calls.

export function ignisScenarioBreakdown(entries) {
  const counts = {
    total: 0,
    unlabeled: 0,
    byScenario: {},
  };
  for (const entry of entries ?? []) {
    if (!entry || entry.status !== "ok" || entry.product !== "ignis") {
      continue;
    }
    counts.total += 1;
    const label = entry.scenario_label;
    if (typeof label === "string" && label.length > 0) {
      counts.byScenario[label] = (counts.byScenario[label] ?? 0) + 1;
    } else {
      counts.unlabeled += 1;
    }
  }
  return counts;
}
