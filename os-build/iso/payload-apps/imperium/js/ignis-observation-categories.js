// IGNIS-ONEOFONE-7 (Del's one-of-one bar, Oct 29): the Ignis
// observation-class breakdown. It counts only what the session log
// actually recorded: the observations inside successful Ignis
// assessments, bucketed by the category each observation itself
// carried — the detail behind each assessment's own verdict, which
// ONEOFONE-1's scoreboard reads at the assessment level. A duty
// officer checking a verdict can see whether the listed
// observations agree with it (a "visible smoke" verdict built on
// "steam or fog" observations reads differently from one built on
// smoke observations), without this panel ever re-scoring anything.
// An assessment with several observations contributes several
// counts; an observation with no usable or non-contract category
// counts in the total only, never inventing a bucket. Per the v2
// contract (js/schema.js) observations live on the response itself;
// the assessment-nested fallback covers entries shaped like the
// ONEOFONE-2 test fixtures, which nest observations under
// assessment. Entries with no usable observations array contribute
// nothing — not even a total — because there is nothing to count.
// Failures contribute nothing (a failed request produced no
// assessment), other products' entries move no bucket, and an
// empty or held session reads all zeros rather than inventing
// observations. This panel never judges whether an observation is
// right, only what class it carried.
//
// Pure read over log entries: no sampling, no model, no live calls.

export function ignisObservationCategories(entries) {
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
    if (!entry || entry.status !== "ok" || entry.product !== "ignis") {
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
