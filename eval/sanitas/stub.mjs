// Fixture assessment source for the Sanitas harness (Agent 3).
// NOT a model. A deterministic stand-in table keyed by scenario_id, so
// the harness can be run and its metric paths exercised with zero
// network access, zero API key, and zero model calls (Spark stays OFF).
//
// The table is deliberately imperfect, and the imperfections are listed
// here so no one mistakes fixture numbers for model performance:
//   - SAN-002 (overflowing bin, poor light) -> "indeterminate" (a miss)
//   - SAN-010 (normal collection, tied bags) -> "waste accumulation"
//     (a false alarm on a confusable negative)
//   - SAN-012 (cardboard box) -> "waste accumulation" (a false alarm)
//   - SAN-014 (cart with belongings) -> "waste accumulation" (a false alarm)
//   - SAN-016 (dark blurry night) -> "clean area" (wrong category, no alert)
//   - SAN-019 (glare frame) -> "clean area" (wrong category, no alert)
// Every other scenario is answered with its labeled category.
// processing.model names the stub itself; latency_ms is null because the
// stub reports no latency — the harness measures its own wall clock.

const TABLE = {
  "SAN-002": {
    category: "indeterminate",
    summary: "Low light prevents a confident determination of the bin state.",
    uncertainty: ["Cannot determine bin state in this light."],
    review: true,
  },
  "SAN-010": {
    category: "waste accumulation",
    summary: "Bags visible at the curb.",
    uncertainty: [],
    review: true,
  },
  "SAN-012": {
    category: "waste accumulation",
    summary: "Cardboard on the sidewalk read as discarded refuse.",
    uncertainty: [],
    review: true,
  },
  "SAN-014": {
    category: "waste accumulation",
    summary: "Items in a cart read as discarded refuse.",
    uncertainty: [],
    review: true,
  },
  "SAN-016": {
    category: "clean area",
    summary: "No refuse discernible in the frame.",
    uncertainty: ["Frame too dark to confirm."],
    review: true,
  },
  "SAN-019": {
    category: "clean area",
    summary: "No refuse discernible in the frame.",
    uncertainty: ["Glare obscures the surface."],
    review: true,
  },
};

const CORRECT = {
  "SAN-001": ["overflowing bin", "Bin overfull with refuse above the rim and bags beside it."],
  "SAN-003": ["waste accumulation", "Loose bags and scattered refuse across the sidewalk."],
  "SAN-004": ["waste accumulation", "Bulky items and bags at a curb with no bin in frame."],
  "SAN-005": ["blocked pedestrian path", "Bins and bags across the full width of the sidewalk."],
  "SAN-006": ["blocked pedestrian path", "Bulky items across a narrow sidewalk."],
  "SAN-007": ["overflowing bin", "Bin overfull at the edge of a tidy collection area."],
  "SAN-008": ["clean area", "Swept sidewalk, no refuse visible."],
  "SAN-009": ["clean area", "Leaves on the ground; no refuse visible."],
  "SAN-011": ["normal collection area", "Closed bins lined up at a curb, no spill."],
  "SAN-013": ["ambiguous object", "A lone chair on a sidewalk; discard status unclear."],
  "SAN-015": ["clean area", "Stains and shadows only; no refuse shapes."],
  "SAN-017": ["indeterminate", "Occlusion hides the deciding detail."],
  "SAN-018": ["indeterminate", "Fog and rain obscure the scene."],
  "SAN-020": ["indeterminate", "Object class cannot be determined in this light."],
};

export async function assessStub(scenario) {
  const entry = TABLE[scenario.scenario_id];
  let category;
  let summary;
  let uncertainty;
  let review;
  if (entry) {
    ({ category, summary, uncertainty, review } = entry);
  } else if (CORRECT[scenario.scenario_id]) {
    [category, summary] = CORRECT[scenario.scenario_id];
    uncertainty = category === "indeterminate" ? ["Cannot determine the condition from this frame."] : [];
    review = category === "ambiguous object" || category === "indeterminate";
  } else {
    throw new Error(`stub has no fixture for scenario ${scenario.scenario_id}`);
  }
  return {
    product: "sanitas",
    timestamp: "2026-10-28T12:00:00.000Z",
    observations: [
      {
        category,
        description: summary,
        evidence: `fixture scene ${scenario.scenario_id}`,
        confidence: null,
      },
    ],
    assessment: {
      category,
      summary,
      uncertainty,
      requires_human_review: review,
    },
    processing: { model: "sanitas-stub-fixture", latency_ms: null },
  };
}
