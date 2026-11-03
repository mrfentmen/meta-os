// Meta Custos eval baseline (fixture).
//
// A fixture that predicts nothing happened for every scenario. It
// passes exactly the one scenario whose honest answer IS the empty
// outcome (CU-EMPTY-01: an empty feed with no hosts and no watched
// domains yields a summary only) and fails every scenario that
// requires a real patrol record. An empty outcome is not a
// verification.

export function assessBaseline(scenario) {
  const pass = scenario.id === "CU-EMPTY-01";
  return {
    pass,
    evidence: pass
      ? "empty outcome: summary only, zero escalations, zero errors"
      : "baseline predicts nothing happened; this scenario requires a patrol record",
  };
}
