// Fixture assessment source for the Medicus harness (Agent 3).
// NOT a model. A deterministic stand-in table keyed by scenario_id, so
// the harness can be run and its metric paths exercised with zero
// network access, zero API key, and zero model calls (Spark stays OFF).
//
// The table is deliberately imperfect, and the imperfections are listed
// here so no one mistakes fixture numbers for model performance:
//   - MED-002 (person on ground, poor light) -> "indeterminate" (a miss)
//   - MED-010 (sunbathing) -> "person on ground"
//     (a false alarm on a confusable negative)
//   - MED-012 (sitting on a curb resting) -> "person on ground" (a false alarm)
//   - MED-013 (CPR training manikin) -> "person on ground" (a false alarm)
//   - MED-016 (dark blurry night) -> "normal activity" (wrong category, no alert)
//   - MED-019 (glare frame) -> "normal activity" (wrong category, no alert)
// Every other scenario is answered with its labeled category.
// processing.model names the stub itself; latency_ms is null because the
// stub reports no latency — the harness measures its own wall clock.

const TABLE = {
  "MED-002": {
    category: "indeterminate",
    summary: "Low light prevents a confident determination of the scene.",
    uncertainty: ["Cannot determine the scene in this light."],
    review: true,
  },
  "MED-010": {
    category: "person on ground",
    summary: "Person lying on a blanket read as a person on the ground.",
    uncertainty: [],
    review: true,
  },
  "MED-012": {
    category: "person on ground",
    summary: "Person sitting on a curb read as a person on the ground.",
    uncertainty: [],
    review: true,
  },
  "MED-013": {
    category: "person on ground",
    summary: "Training manikin read as a person on the ground.",
    uncertainty: [],
    review: true,
  },
  "MED-016": {
    category: "normal activity",
    summary: "No incident discernible in the frame.",
    uncertainty: ["Frame too dark to confirm."],
    review: true,
  },
  "MED-019": {
    category: "normal activity",
    summary: "No incident discernible in the frame.",
    uncertainty: ["Glare obscures the scene."],
    review: true,
  },
};

const CORRECT = {
  "MED-001": ["person on ground", "Person lying on a sidewalk in daylight."],
  "MED-003": ["crowd gathered around a person", "Crowd standing close around a person on the ground."],
  "MED-004": ["vehicle collision scene", "Two vehicles with visible damage, people nearby."],
  "MED-005": ["blocked crew access", "Vehicle and debris across the only path to the scene."],
  "MED-006": ["person motionless", "Person lying still on the ground."],
  "MED-007": ["person on ground", "Person on the ground beside a transit stop."],
  "MED-008": ["normal activity", "Pedestrians walking, no incident visible."],
  "MED-009": ["normal activity", "Person sleeping on a bench; no incident visible."],
  "MED-011": ["normal activity", "Person stretching on a mat outdoors."],
  "MED-014": ["normal activity", "Person sitting on the ground resting against a wall."],
  "MED-015": ["normal activity", "Stains and shadows only; no person visible."],
  "MED-017": ["indeterminate", "Occlusion hides the deciding detail."],
  "MED-018": ["indeterminate", "Fog and rain obscure the scene."],
  "MED-020": ["indeterminate", "Figure class cannot be determined in this light."],
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
    review = category === "indeterminate";
  } else {
    throw new Error(`stub has no fixture for scenario ${scenario.scenario_id}`);
  }
  return {
    product: "medicus",
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
    processing: { model: "medicus-stub-fixture", latency_ms: null },
  };
}
