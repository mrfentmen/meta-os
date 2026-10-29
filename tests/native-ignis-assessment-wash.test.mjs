// Node built-in test runner, no dependencies:
//   node --test tests/native-ignis-assessment-wash.test.mjs
//
// IGNIS-UI-6 (Del UI push, Oct 29): native latest-assessment panel
// product-accent wash parity. The web panel carries a per-product
// gradient (R2/UI-3: 0.09 red at the top on Ignis) and the native
// panel carries the UI-5 3pt leading rule in the assessment's own
// accent, but the native panel body itself was unwashed, so the
// panel read flat while its web counterpart carried the product
// tint. The fix adds a flat 0.09 wash in the assessment's own
// accent behind the whole outer stack, matching the web gradient's
// top strength. No Swift toolchain exists in this sandbox, so these
// are static checks on the shipped Swift.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const assessment = readFileSync(
  new URL(
    "../native/Sources/MetaTrio/Views/AssessmentView.swift",
    import.meta.url,
  ),
  "utf8",
);
const productConfig = readFileSync(
  new URL(
    "../native/Sources/MetaTrio/Models/ProductConfig.swift",
    import.meta.url,
  ),
  "utf8",
);

const bodyFn = assessment.slice(assessment.indexOf("var body: some View"));
assert.ok(bodyFn.length > 0, "body exists");

test("native assessment panel: outer stack carries a 0.09 accent wash behind the panel", () => {
  assert.match(
    bodyFn,
    /\.overlay\(alignment: \.leading\) \{\s+Rectangle\(\)\s+\.fill\(accentColor\)\s+\.frame\(width: 3\)\s+\}[\s\S]*?\.background\(accentColor\.opacity\(0\.09\)\)/,
    "wash sits on the outer stack after the UI-5 rule, so the whole panel — not one section — carries it",
  );
  const washes = bodyFn.match(/\.background\(accentColor\.opacity\(0\.09\)\)/g) || [];
  assert.equal(washes.length, 1, "exactly one panel wash");
});

test("native assessment panel: wash color comes from the assessment's own product, not the selection", () => {
  assert.doesNotMatch(
    assessment,
    /selectedProduct/,
    "AssessmentView never consults the selected product",
  );
  const helper = assessment.slice(assessment.indexOf("private var accentColor"));
  assert.ok(helper.length > 0, "accentColor helper exists");
  assert.match(
    helper,
    /switch ProductID\(rawValue: response\.product\)\?\.config\.accentColorName \{\s+case "blue": return \.blue\s+case "red": return \.red\s+case "green": return \.green/,
    "wash shares the UI-5 helper mapping, so it tracks the assessment product",
  );
});

test("native assessment panel: Ignis assessments wash red", () => {
  const ignis = productConfig.slice(productConfig.indexOf("static let ignis"));
  assert.match(
    ignis,
    /accentColorName: "red"/,
    "Ignis accentColorName is red (R1), so Ignis assessment panels wash red",
  );
});

test("native assessment panel: wash adds no second rule", () => {
  const rectangles = assessment.match(/Rectangle\(\)/g) || [];
  assert.equal(
    rectangles.length,
    1,
    "exactly one Rectangle — the UI-5 rule; the wash is a background, not another edge",
  );
});
