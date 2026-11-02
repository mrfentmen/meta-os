// Validator enforcement tests (LANE A fix, 2026-10-30):
// validateAssessment now enforces (a) category membership in the
// selected product's own category list from js/products.js, for
// both the assessment category and every observation category, and
// (b) Medicus requires_human_review === true. Before this fix the
// validator accepted any non-empty category string and any boolean
// for the review flag.

import test from "node:test";
import assert from "node:assert/strict";

import { validateAssessment } from "../js/schema.js";
import { PRODUCTS, PRODUCT_BY_ID } from "../js/products.js";

function assessmentFor(productId, { category, observationCategory, review } = {}) {
  const product = PRODUCT_BY_ID[productId];
  const own = product.categories[0];
  return {
    product: productId,
    timestamp: "2026-10-30T12:00:00.000Z",
    observations: [
      {
        category: observationCategory ?? category ?? own,
        description: "Something visible.",
        evidence: "center of frame",
        confidence: 0.5,
      },
    ],
    assessment: {
      category: category ?? own,
      summary: "Summary.",
      uncertainty: [],
      requires_human_review: review ?? (productId === "medicus" ? true : false),
    },
    processing: { model: "test-double", latency_ms: 5 },
  };
}

test("enforcement: every product's own categories validate for that product", () => {
  for (const product of PRODUCTS) {
    for (const category of product.categories) {
      const check = validateAssessment(assessmentFor(product.id, { category }), product.id);
      assert.equal(check.ok, true, `${product.id} / ${category}: ${check.errors.join("; ")}`);
    }
  }
});

test("enforcement: an assessment category from another division is rejected", () => {
  const check = validateAssessment(
    assessmentFor("vigiles", { category: "visible smoke", observationCategory: "energetic movement" }),
    "vigiles",
  );
  assert.equal(check.ok, false);
  assert.ok(check.errors.some((e) => e.includes("assessment.category") && e.includes("not a permitted category")));
});

test("enforcement: an observation category outside the product set is rejected", () => {
  const check = validateAssessment(
    assessmentFor("ignis", { category: "visible smoke", observationCategory: "person down" }),
    "ignis",
  );
  assert.equal(check.ok, false);
  assert.ok(
    check.errors.some((e) => e.includes("observations[0].category") && e.includes("not a permitted category")),
  );
});

test("enforcement: an invented category is rejected for every product", () => {
  for (const product of PRODUCTS) {
    const check = validateAssessment(
      assessmentFor(product.id, { category: "not a real category" }),
      product.id,
    );
    assert.equal(check.ok, false, `${product.id} must reject an invented category`);
  }
});

test("enforcement: Medicus with requires_human_review false is rejected", () => {
  const check = validateAssessment(assessmentFor("medicus", { review: false }), "medicus");
  assert.equal(check.ok, false);
  assert.ok(check.errors.some((e) => e.includes("requires_human_review") && e.includes("medicus")));
});

test("enforcement: Medicus with requires_human_review true passes; other divisions may be false", () => {
  assert.equal(validateAssessment(assessmentFor("medicus", { review: true }), "medicus").ok, true);
  assert.equal(validateAssessment(assessmentFor("vigiles", { review: false }), "vigiles").ok, true);
  assert.equal(validateAssessment(assessmentFor("ignis", { review: false }), "ignis").ok, true);
});

test("region: a valid bounding box passes; null and absent pass", () => {
  const withBox = assessmentFor("vigiles", {});
  withBox.observations[0].region = { x: 100, y: 200, w: 300, h: 400 };
  assert.equal(validateAssessment(withBox, "vigiles").ok, true);
  const withNull = assessmentFor("vigiles", {});
  withNull.observations[0].region = null;
  assert.equal(validateAssessment(withNull, "vigiles").ok, true);
  assert.equal(validateAssessment(assessmentFor("vigiles", {}), "vigiles").ok, true);
});

test("region: malformed boxes are rejected", () => {
  for (const bad of [{ x: -1, y: 0, w: 10, h: 10 }, { x: 0, y: 0, w: 0, h: 10 }, { x: 0.5, y: 0, w: 10, h: 10 }, { x: 0, y: 0, w: 10 }, "left side", 42]) {
    const a = assessmentFor("vigiles", {});
    a.observations[0].region = bad;
    const check = validateAssessment(a, "vigiles");
    assert.equal(check.ok, false, JSON.stringify(bad));
    assert.ok(check.errors.some((e) => e.includes("region")), JSON.stringify(bad));
  }
});

test("region: vigiles 'crowd gathered' is a permitted category", () => {
  const check = validateAssessment(assessmentFor("vigiles", { category: "crowd gathered" }), "vigiles");
  assert.equal(check.ok, true, check.errors.join("; "));
});
