// IGNIS-ONEOFONE-12 (Del's one-of-one bar, Oct 30): the Ignis
// review queue by model, in honest form. It counts only what the
// session log actually recorded: the assessments already awaiting
// human review — recorded ok Ignis assessments whose assessment
// itself carried requires_human_review === true (the ONEOFONE-3
// queue) — split by the model string each assessment itself
// reported in response.processing.model (the ONEOFONE-8 field, a
// v2 contract field, js/schema.js). A duty officer opening the
// queue can see at a glance which model is producing the flagged
// work — say, one model dominating the queue after a Spark
// transport change — without this panel ever re-flagging anything
// itself. Clear and unknown-flag entries are not awaiting review
// and move no bucket, exactly as in ONEOFONE-6's triage; failures
// contribute nothing (a failed request produced no assessment),
// other products' entries move no bucket, and a flagged entry
// with no usable model string (missing processing, missing model,
// empty or non-string model — recorded before attribution existed,
// or restored from an older export) still counts in the total and
// in unattributed, never inventing a model name. Model names are
// open-ended (the contract requires only a non-empty string), so
// buckets live in a byModel map keyed by the exact reported
// string; rendering sorts the keys so the panel line is stable.
// An empty or held session reads all zeros rather than inventing
// a queue mix. This panel never judges whether a flag was right,
// only which model the record says produced each flagged
// assessment.
//
// Pure read over log entries: no sampling, no model, no live calls.

export function ignisReviewByModel(entries) {
  const counts = {
    totalFlagged: 0,
    unattributed: 0,
    byModel: {},
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
    const model = entry.response?.processing?.model;
    if (typeof model === "string" && model.length > 0) {
      counts.byModel[model] = (counts.byModel[model] ?? 0) + 1;
    } else {
      counts.unattributed += 1;
    }
  }
  return counts;
}
