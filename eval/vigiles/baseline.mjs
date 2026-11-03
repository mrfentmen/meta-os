// Baseline assessment source for the Vigiles harness (Hana's lane).
// The simplest possible baseline: predict "normal activity" for
// every scene, fire no alert, perform no scene review. It exists so
// the harness can show, honestly, what a do-nothing source scores
// against the same ground truth: precision undefined (no alert ever
// predicted), recall 0, false-positive rate 0, false-negative rate 1.
// Any future assessment source must beat this baseline's recall and
// decided-row category accuracy to claim it adds value; beating it
// on precision alone proves nothing, since the baseline never fires
// a false alarm by construction. Mirrors eval/medicus/baseline.mjs,
// which predicts "normal activity" for the Medicus product; this file
// touches no Medicus file. No network, no model calls, no inspection
// of the scenario: the scenario argument is accepted only to satisfy
// the source contract (an async function assess(scenario)).

export async function assessBaseline(_scenario) {
  return {
    product: "vigiles",
    timestamp: "2026-10-28T12:00:00.000Z",
    observations: [],
    assessment: {
      category: "normal activity",
      summary: "Baseline predicts normal activity for every scene; it performs no scene review.",
      uncertainty: ["Baseline performs no scene review."],
      requires_human_review: false,
    },
    processing: { model: "vigiles-baseline-always-normal", latency_ms: null },
  };
}
