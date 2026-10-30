// IGNIS-ONEOFONE-16 (Del's one-of-one bar, Oct 30): the Ignis
// review queue by observation category, in honest form. It counts
// only what the session log actually recorded: the observations
// inside assessments already awaiting human review — recorded ok
// Ignis assessments whose assessment itself carried
// requires_human_review === true (the ONEOFONE-3 queue) —
// bucketed by the category each observation itself carried, the
// same contract categories ONEOFONE-7's breakdown reads for all
// successful Ignis assessments and ONEOFONE-6's triage reads at
// the assessment level. A duty officer opening the queue can see
// at a glance which observation classes the flagged work rests
// on — say, flagged work built on "steam or fog" observations
// versus on smoke observations — without this panel ever
// re-scoring anything or judging whether a flag was right. An
// assessment with several observations contributes several
// counts; an observation with no usable or non-contract category
// counts in the total only, never inventing a bucket. Clear and
// unknown-flag entries are not awaiting review and move no
// bucket, failures contribute nothing (a failed request produced
// no assessment), other products' entries move no bucket, and a
// flagged entry with no usable observations array contributes
// nothing — not even a total — because there is nothing to
// count. Per the v2 contract (js/schema.js) observations live on
// the response itself; the assessment-nested fallback covers
// entries shaped like the ONEOFONE-2 test fixtures, which nest
// observations under assessment, exactly as ONEOFONE-7 does. An
// empty or held session reads all zeros rather than inventing a
// queue mix.
//
// Pure read over log entries: no sampling, no model, no live calls.

export function ignisReviewByObservationCategory(entries) {
  const counts = {
    total: 0,
    visibleSmoke: 0,
    visibleFlame: 0,
    steamOrFog: 0,
    flameLikeLighting: 0,
    obscuredOrDistant: 0,
    noHazard: 0,
    indeterminate: 0,
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
    const response = entry.response;
    const observations = Array.isArray(response?.observations)
      ? response.observations
      : response?.assessment?.observations;
    if (!Array.isArray(observations)) {
      continue;
    }
    for (const obs of observations) {
      counts.total += 1;
      switch (obs?.category) {
        case "visible smoke":
          counts.visibleSmoke += 1;
          break;
        case "visible flame":
          counts.visibleFlame += 1;
          break;
        case "steam or fog":
          counts.steamOrFog += 1;
          break;
        case "flame-like lighting":
          counts.flameLikeLighting += 1;
          break;
        case "obscured or distant hazard":
          counts.obscuredOrDistant += 1;
          break;
        case "no hazard visible":
          counts.noHazard += 1;
          break;
        case "indeterminate":
          counts.indeterminate += 1;
          break;
        default:
          break;
      }
    }
  }
  return counts;
}
