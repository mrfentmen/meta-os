// IGNIS-ONEOFONE-1 (Del's one-of-one bar, Oct 29): the Ignis
// look-alike scoreboard. It counts only what the session log actually
// recorded: successful Ignis assessments, bucketed by the category the
// assessment itself returned. The two look-alike classes from the
// contract (js/products.js) — "steam or fog" and "flame-like lighting"
// — read against the two hazard classes ("visible smoke", "visible
// flame"); the remaining three contract categories read as Other.
// Dust has no Ignis category of its own, so a dust-like scene never
// invents a bucket here: it counts under whatever category its
// assessment actually returned, or in the total only when that
// category is not a contract category. Failures contribute nothing
// (a failed request produced no assessment), other products' entries
// move no bucket, and an ok entry with no usable assessment category
// still counts in the total — the total is the recorded Ignis
// successes, and the named buckets never sum past it. Pure read over
// log entries: no sampling, no model, no live calls.

export function ignisLookAlikeScoreboard(entries) {
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
    counts.total += 1;
    switch (entry.response?.assessment?.category) {
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
  return counts;
}
