// Meta Hands-Free eval baseline (first slice): the empty-outcome reader.
//
// A fixture, not a model and not a run. It predicts the empty outcome
// for every scenario: nothing filed, "No orders ran.", no approval, no
// latency, no voice line. It therefore passes exactly the two scenarios
// whose honest answer IS the empty outcome (HF-INTAKE-EMPTY-01,
// HF-BRIEF-EMPTY-01) and fails every scenario that requires an actual
// read or run. That is the bar a real run must beat: chanting "nothing
// happened" scores 2/13; running the real modules scores 13/13. An
// empty outcome is not a verification.

const LABEL_ONLY_PASS = new Set(["HF-INTAKE-EMPTY-01", "HF-BRIEF-EMPTY-01"]);

export function assessBaseline(scenario) {
  if (LABEL_ONLY_PASS.has(scenario.id)) {
    return { pass: true, evidence: "empty-outcome reader: predicts nothing happened (empty outcome matches by chant)" };
  }
  return { pass: false, evidence: "empty-outcome reader: predicts nothing happened (this scenario needs a real module)" };
}
