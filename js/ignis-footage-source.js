// IGNIS-ONEOFONE-9 (Del's one-of-one bar, Oct 29): the Ignis
// recorded-footage mode, in honest form. It counts only what the
// session log actually recorded: the recorded ok Ignis assessments,
// bucketed by the input source the app itself stamped on each entry
// when the request was made — "live-camera" for a frame sampled
// from the live camera, "still-image" for an uploaded still image,
// "recorded-video" for a frame captured from an uploaded video
// file (the FDNY recorded-footage workflow: prerecorded footage
// assessed after the fact, never a live feed claimed as recorded
// or vice versa). The source is stamped at submit time by the
// path that genuinely knows it (js/app.js), never inferred after
// the fact from the image or the assessment. An entry with no
// usable source — recorded before this field existed, restored
// from an older export, or hand-built — counts in the total and
// in unknown, never guessed into a bucket. Failures contribute
// nothing (a failed request produced no assessment), other
// products' entries move no bucket, and an empty or held session
// reads all zeros rather than inventing a footage mix. This panel
// never claims a source is recorded footage when the log does
// not say so, and never judges whether a source was right.
//
// Pure read over log entries: no sampling, no model, no live calls.

export function ignisFootageSource(entries) {
  const counts = {
    total: 0,
    liveCamera: 0,
    stillImage: 0,
    recordedVideo: 0,
    unknown: 0,
  };
  for (const entry of entries ?? []) {
    if (!entry || entry.status !== "ok" || entry.product !== "ignis") {
      continue;
    }
    counts.total += 1;
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
        counts.unknown += 1;
        break;
    }
  }
  return counts;
}
