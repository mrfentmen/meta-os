// IGNIS-ONEOFONE-4 (Del's one-of-one bar, Oct 29): the Ignis
// transparent-eval panel. It counts only what the session log
// actually recorded: successful Ignis assessments, bucketed by
// whether their observations carry evidence a human reviewer can
// actually inspect. Fully evidenced means every observation carries
// a non-empty evidence string; partially evidenced means some but
// not all do; unevidenced means no observation carries one (an
// empty observations array counts here — a recorded assessment with
// nothing to inspect); unassessable means the entry carries no
// usable observations array at all — a restored or hand-built entry
// the panel refuses to guess about, never a silent unevidenced.
// Per the v2 contract (js/schema.js) observations live on the
// response itself; the assessment-nested fallback covers entries
// shaped like the ONEOFONE-2 test fixtures, which nest observations
// under assessment. Failures contribute nothing (a failed request
// produced no assessment), other products' entries move no bucket,
// and an empty or held session reads all zeros rather than
// inventing transparency. This is a reading of recorded evidence
// strings only: it never judges whether the evidence is good, never
// re-scores an assessment, and never claims an assessment is
// correct because its evidence field is filled in.
//
// Pure read over log entries: no sampling, no model, no live calls.

export function ignisEvidenceTransparency(entries) {
  const counts = {
    total: 0,
    fullyEvidenced: 0,
    partiallyEvidenced: 0,
    unevidenced: 0,
    unassessable: 0,
  };
  for (const entry of entries ?? []) {
    if (!entry || entry.status !== "ok" || entry.product !== "ignis") {
      continue;
    }
    counts.total += 1;
    const response = entry.response;
    const observations = Array.isArray(response?.observations)
      ? response.observations
      : response?.assessment?.observations;
    if (!Array.isArray(observations)) {
      counts.unassessable += 1;
      continue;
    }
    let evidenced = 0;
    for (const obs of observations) {
      if (typeof obs?.evidence === "string" && obs.evidence.trim().length > 0) {
        evidenced += 1;
      }
    }
    if (observations.length > 0 && evidenced === observations.length) {
      counts.fullyEvidenced += 1;
    } else if (evidenced > 0) {
      counts.partiallyEvidenced += 1;
    } else {
      counts.unevidenced += 1;
    }
  }
  return counts;
}
