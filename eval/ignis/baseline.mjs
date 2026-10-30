// Baseline assessment source for the Ignis harness (Rowan's lane).
// The simplest possible baseline: predict "no hazard visible" for
// every scene, fire no alert, perform no inspection. It exists so the
// harness can show, honestly, what a do-nothing source scores against
// the same ground truth: precision undefined (no alert ever
// predicted), recall 0, false-positive rate 0, false-negative rate 1.
// Any future assessment source must beat this baseline's recall and
// category accuracy to claim it adds value; beating it on precision
// alone proves nothing, since the baseline never fires a false alarm
// by construction. Mirrors eval/medicus/baseline.mjs, which predicts
// "normal activity" for the Medicus product; this file touches no Medicus
// file. No network, no model calls, no inspection of the scenario:
// the scenario argument is accepted only to satisfy the source
// contract (an async function assess(scenario)).

export async function assessBaseline(_scenario) {
  return {
    product: "ignis",
    timestamp: "2026-10-28T12:00:00.000Z",
    observations: [],
    assessment: {
      category: "no hazard visible",
      summary: "Baseline predicts no hazard for every scene; it performs no inspection.",
      uncertainty: ["Baseline performs no inspection."],
      requires_human_review: false,
    },
    processing: { model: "ignis-baseline-always-no-hazard", latency_ms: null },
  };
}
