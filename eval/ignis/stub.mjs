// Fixture assessment source for the Ignis harness (Rowan's lane).
// NOT a model. A deterministic stand-in table keyed by scenario_id, so
// the harness can be run and its metric paths exercised with zero
// network access, zero API key, and zero model calls (Spark stays OFF).
// Mirrors eval/sanitas/stub.mjs, which does the same for Sanitas;
// this file touches no Sanitas file.
//
// The table is deliberately imperfect, and the imperfections are listed
// here so no one mistakes fixture numbers for model performance:
//   - IGN-003 (visible smoke, poor lighting, night) -> "indeterminate"
//     (a miss: a real alert missed, FN)
//   - IGN-007 (steam from a vent) -> "visible smoke"
//     (a false alarm on a confusable negative, FP)
//   - IGN-010 (orange neon signage) -> "visible flame"
//     (a false alarm on a confusable negative, FP)
//   - IGN-012 (flame glow behind frosted glass, obscured) ->
//     "flame-like lighting" (wrong category, no alert)
//   - IGN-015 (fog and rain, indeterminate) -> "steam or fog"
//     (wrong category, no alert)
//   - IGN-018 (vehicle lights in rain, flame-like lighting) ->
//     "visible flame" (a false alarm on a confusable negative, FP)
// Every other scenario is answered with its labeled category.
// processing.model names the stub itself; latency_ms is null because the
// stub reports no latency — the harness measures its own wall clock.

const TABLE = {
  "IGN-003": {
    category: "indeterminate",
    summary: "Low light prevents a confident determination of the smoke column.",
    uncertainty: ["Cannot determine the condition in this light."],
    review: true,
  },
  "IGN-007": {
    category: "visible smoke",
    summary: "White vapor from the vent read as a smoke plume.",
    uncertainty: [],
    review: true,
  },
  "IGN-010": {
    category: "visible flame",
    summary: "Orange signage glow read as open flame.",
    uncertainty: [],
    review: true,
  },
  "IGN-012": {
    category: "flame-like lighting",
    summary: "Warm glow behind frosted glass read as lighting, not a hazard.",
    uncertainty: ["Flame itself is occluded; presence cannot be confirmed."],
    review: true,
  },
  "IGN-015": {
    category: "steam or fog",
    summary: "Fog and rain read as a weather condition, not indeterminacy.",
    uncertainty: ["Weather obscures the scene."],
    review: true,
  },
  "IGN-018": {
    category: "visible flame",
    summary: "Vehicle lights streaking through rain read as flame.",
    uncertainty: [],
    review: true,
  },
};

const CORRECT = {
  "IGN-001": ["visible smoke", "Grey smoke plume rising from a rooftop vent stack.", true],
  "IGN-002": ["visible flame", "Open flames visible in prerecorded footage.", true],
  "IGN-004": ["visible flame", "Flames with a smoke plume above them in prerecorded footage.", true],
  "IGN-005": ["no hazard visible", "Quiet residential street, no smoke, flame, or haze.", false],
  "IGN-006": ["no hazard visible", "Kitchen in daylight, no smoke, flame, or steam visible.", false],
  "IGN-008": ["steam or fog", "Morning fog lying low over a street, ground-hugging.", false],
  "IGN-009": ["flame-like lighting", "Sunset glow across building windows, flat and static.", false],
  "IGN-011": ["obscured or distant hazard", "Faint smoke column on the far horizon, partly hidden.", true],
  "IGN-013": ["indeterminate", "Night scene too dark and blurred to determine any condition.", true],
  "IGN-014": ["indeterminate", "Frame washed out by direct sun glare.", true],
  "IGN-016": ["visible smoke", "Clear smoke plume from a controlled visual demonstration.", true],
  "IGN-017": ["no hazard visible", "Empty parking lot at noon, no smoke, flame, or haze.", false],
  "IGN-019": ["obscured or distant hazard", "Thin haze only at the far edge of the frame, unconfirmable.", true],
  "IGN-020": ["indeterminate", "Unidentifiable glowing shape at dusk.", true],
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
    [category, summary, review] = CORRECT[scenario.scenario_id];
    uncertainty = category === "indeterminate" ? ["Cannot determine the condition from this frame."] : [];
  } else {
    throw new Error(`stub has no fixture for scenario ${scenario.scenario_id}`);
  }
  return {
    product: "ignis",
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
    processing: { model: "ignis-stub-fixture", latency_ms: null },
  };
}
