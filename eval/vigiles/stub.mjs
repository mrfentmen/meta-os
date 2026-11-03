// Fixture assessment source for the Vigiles harness (Hana's lane).
// NOT a model. A deterministic stand-in table keyed by scenario_id,
// so the harness can be run and its metric paths exercised with zero
// network access, zero API key, and zero model calls (Spark stays OFF).
// Mirrors eval/ignis/stub.mjs, which does the same for Ignis; this
// file touches no Ignis or Medicus file.
//
// The table reproduces the RECORDED batch-6 outcomes from
// os-build/demo/EVAL4.md (the same verdicts the fixture file cites),
// so no number here is a new claim:
//   - VIG-F01 (crowd gathered) -> "crowd gathered" (batch 6 MATCH;
//     batch 3 had missed it because vigiles had no crowd class, and
//     batch 4's crowd fix held through batch 6)
//   - VIG-F02 (normal activity) -> "normal activity" (batch 6 MATCH;
//     batch 4's false flag on ordinary pedestrian traffic was fixed
//     in batch 5 by narrowing "crowd gathered" to a stationary
//     assembled crowd)
//   - VIG-F03 (public disturbance / altercation) -> "crowd gathered"
//     (batch 6 HELD: true of the protest scene, but the altercation
//     class was never committed to, so the row routes to human
//     review — a designed safe outcome, not a miss. Its products
//     category is undecided by the fixture, so the harness scores
//     its category as undecided, never as wrong, and its alert as a
//     false negative against the fixture's alert_expected=true.)
// processing.model names the stub itself; latency_ms is null because
// the stub reports no latency — the harness measures its own wall clock.

const TABLE = {
  "VIG-F01": {
    category: "crowd gathered",
    summary: "A very large crowd gathered in a public space, seen from directly overhead.",
    uncertainty: [],
    review: false,
  },
  "VIG-F02": {
    category: "normal activity",
    summary: "Pedestrians crossing at a busy intersection, ordinary pedestrian traffic in motion.",
    uncertainty: [],
    review: false,
  },
  "VIG-F03": {
    category: "crowd gathered",
    summary: "A protest confrontation at close quarters; crowd gathered named, altercation not committed to.",
    uncertainty: ["Whether the pushing at the police line amounts to the altercation class is not determined here."],
    review: true,
  },
};

export async function assessStub(scenario) {
  const entry = TABLE[scenario.scenario_id];
  if (!entry) {
    throw new Error(`stub has no fixture for scenario ${scenario.scenario_id}`);
  }
  return {
    product: "vigiles",
    timestamp: "2026-10-28T12:00:00.000Z",
    observations: [
      {
        category: entry.category,
        description: entry.summary,
        evidence: `fixture scene ${scenario.scenario_id}`,
        confidence: null,
      },
    ],
    assessment: {
      category: entry.category,
      summary: entry.summary,
      uncertainty: entry.uncertainty,
      requires_human_review: entry.review,
    },
    processing: { model: "vigiles-stub-fixture", latency_ms: null },
  };
}
