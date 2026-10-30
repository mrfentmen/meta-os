// IGNIS-ONEOFONE-13 (Del's one-of-one bar, Oct 30): the Ignis
// review audit trail, in honest form. It counts only what the
// session log actually recorded: the recorded ok Ignis
// assessments already awaiting human review (requires_human_review
// === true, the ONEOFONE-3 queue), bucketed by how complete the
// provenance trail each entry itself carries is. A duty officer
// verifying a flagged assessment needs to trace it back — when it
// was requested, which model reported it, which staged scenario
// it came from, and which input path produced it — and this panel
// says how many queued items can actually be traced that far,
// without ever filling a gap from elsewhere. The four trail
// fields are the ones the log itself stamps: request_timestamp
// (a non-empty string, js/log.js), the model string the
// assessment itself reported (response.processing.model, the
// ONEOFONE-8 field), the scenario label the operator supplied
// (scenario_label, the ONEOFONE-10 field), and the input source
// stamped at submit time (source, one of live-camera, still-image,
// or recorded-video, the ONEOFONE-9 field). Full trail means all
// four are present and usable; no trail means none of them is;
// partial trail means one to three. Clear and unknown-flag
// entries are not awaiting review and move no bucket, failures
// contribute nothing (a failed request produced no assessment),
// other products' entries move no bucket, and an empty or held
// session reads all zeros rather than inventing a queue. This
// panel never judges whether a flag was right, never assigns a
// missing field, and never claims a trail the log does not
// record.
//
// Pure read over log entries: no sampling, no model, no live calls.

const KNOWN_SOURCES = new Set(["live-camera", "still-image", "recorded-video"]);

function usableString(value) {
  return typeof value === "string" && value.length > 0;
}

export function ignisReviewAuditTrail(entries) {
  const counts = {
    totalFlagged: 0,
    fullTrail: 0,
    partialTrail: 0,
    noTrail: 0,
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
    let present = 0;
    if (usableString(entry.request_timestamp)) present += 1;
    if (usableString(entry.response?.processing?.model)) present += 1;
    if (usableString(entry.scenario_label)) present += 1;
    if (KNOWN_SOURCES.has(entry.source)) present += 1;
    if (present === 4) {
      counts.fullTrail += 1;
    } else if (present === 0) {
      counts.noTrail += 1;
    } else {
      counts.partialTrail += 1;
    }
  }
  return counts;
}
