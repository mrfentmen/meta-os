// IGNIS-ONEOFONE-6 (Del's one-of-one bar, Oct 29): the Ignis
// review triage panel. It counts only what the session log actually
// recorded: successful Ignis assessments the assessment itself
// flagged for human review (requires_human_review === true, the same
// flag ONEOFONE-3's queue reads), bucketed by the category the
// assessment itself returned — the same contract categories
// ONEOFONE-1's scoreboard reads. A duty officer opening the queue
// sees at a glance which hazard classes are awaiting verification,
// rather than one undifferentiated flagged count. An entry counts
// only when its flag is exactly true: clear (false) and unknown
// (missing or non-boolean) entries are not awaiting review and move
// no bucket, not even the total — the total is the flagged queue,
// and the named buckets never sum past it. A flagged entry with no
// usable assessment category still counts in the total — the queue
// holds it even though no class can be named for it — and a flagged
// entry carrying a non-contract category likewise counts in the
// total only, never inventing a bucket. Failures contribute nothing
// (a failed request produced no assessment), other products'
// entries move no bucket, and an empty or held session reads all
// zeros rather than inventing a queue. This panel never flags
// anything itself, never re-scores an assessment, and never
// notifies anyone — reaching out stays a human action.
//
// Pure read over log entries: no sampling, no model, no live calls.

export function ignisReviewTriage(entries) {
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
    if (entry.response?.assessment?.requires_human_review !== true) {
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
