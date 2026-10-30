// IGNIS-ONEOFONE-11 (Del's one-of-one bar, Oct 30): the Ignis
// review queue by footage source, in honest form. It counts only
// what the session log actually recorded: the assessments already
// awaiting human review — recorded ok Ignis assessments whose
// assessment itself carried requires_human_review === true (the
// ONEOFONE-3 queue) — split by the input source each entry was
// stamped with at submit time (the ONEOFONE-9 stamp: live camera,
// still image, or recorded video). A duty officer opening the
// queue can see at a glance which input path is producing the
// flagged work — say, recorded video dominating the queue after
// a footage-review session — without this panel ever re-flagging
// anything itself. Clear and unknown-flag entries are not awaiting
// review and move no bucket, exactly as in ONEOFONE-6's triage;
// failures contribute nothing (a failed request produced no
// assessment), other products' entries move no bucket, and a
// flagged entry with no usable source stamp (recorded before the
// stamp existed, or restored from an older export) still counts
// in the total and in unknownSource, never guessed into a bucket.
// An empty or held session reads all zeros rather than inventing
// a queue mix. This panel never judges whether a flag was right,
// only where the flagged assessments came from.
//
// Pure read over log entries: no sampling, no model, no live calls.

export function ignisReviewBySource(entries) {
  const counts = {
    totalFlagged: 0,
    liveCamera: 0,
    stillImage: 0,
    recordedVideo: 0,
    unknownSource: 0,
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
    switch (entry.source) {
      case "live-camera":
        counts.liveCamera += 1;
        break;
      case "still-image":
        counts.stillImage += 1;
        break;
      case "recorded-video":
        counts.recordedVideo += 1;
        break;
      default:
        counts.unknownSource += 1;
        break;
    }
  }
  return counts;
}
