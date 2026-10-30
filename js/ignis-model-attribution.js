// IGNIS-ONEOFONE-8 (Del's one-of-one bar, Oct 29): the Ignis
// model-attribution breakdown. It counts only what the session log
// actually recorded: the recorded ok Ignis assessments, bucketed by
// the model string each assessment itself reported in
// response.processing.model (a v2 contract field, js/schema.js) —
// so a duty officer can see which model produced which verdicts
// without this panel ever naming a model the log did not record.
// An assessment with no usable model string (missing processing,
// missing model, empty or non-string model) counts in the total and
// in unattributed, never inventing a model name. Failures
// contribute nothing (a failed request produced no assessment),
// other products' entries move no bucket, and an empty or held
// session reads all zeros rather than inventing attributions.
// This panel never judges whether a model was right, only which
// model the record says produced each assessment. The model names
// are open-ended (the contract requires only a non-empty string),
// so buckets live in a byModel map keyed by the exact reported
// string; rendering sorts the keys so the panel line is stable.
//
// Pure read over log entries: no sampling, no model, no live calls.

export function ignisModelAttribution(entries) {
  const counts = {
    total: 0,
    unattributed: 0,
    byModel: {},
  };
  for (const entry of entries ?? []) {
    if (!entry || entry.status !== "ok" || entry.product !== "ignis") {
      continue;
    }
    counts.total += 1;
    const model = entry.response?.processing?.model;
    if (typeof model === "string" && model.length > 0) {
      counts.byModel[model] = (counts.byModel[model] ?? 0) + 1;
    } else {
      counts.unattributed += 1;
    }
  }
  return counts;
}
