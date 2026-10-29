// Node built-in test runner, no dependencies:
//   node --test tests/native-ignis-assessment-panel.test.mjs
//
// IGNIS-UI-5 (Del UI push, Oct 29): native latest-assessment panel
// product-accent edge parity. The web panel carries a per-product
// gradient (Ignis red #d92b2b via R2) and the native timeline rows
// carry a 3pt leading rule in the entry's own product accent (UI-4),
// but the native AssessmentView panel carried no accent marker at
// all, so a redisplayed assessment looked identical under every
// product. The fix adds a 3pt leading rule to the outer stack in the
// assessment's own product accent, mirroring the UI-4 pattern. No
// Swift toolchain exists in this sandbox, so these are static checks
// on the shipped Swift.

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

test("native assessment panel: outer stack carries a 3pt accent leading rule", () => {
  assert.match(
    bodyFn,
    /\.padding\(\.leading, 10\)\s+\.overlay\(alignment: \.leading\) \{\s+Rectangle\(\)\s+\.fill\(accentColor\)\s+\.frame\(width: 3\)/,
    "outer stack has a 3pt leading rule in the assessment accent, with the UI-4 10pt leading padding",
  );
});

test("native assessment panel: rule color comes from the assessment's own product, not the selection", () => {
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
    "helper maps the assessment product's accentColorName, same mapping as TimelineView",
  );
});

test("native assessment panel: Ignis assessments resolve to red", () => {
  const ignis = productConfig.slice(productConfig.indexOf("static let ignis"));
  assert.match(
    ignis,
    /accentColorName: "red"/,
    "Ignis accentColorName is red (R1), so Ignis assessment panels are red",
  );
});

test("native assessment panel: rule is not confined to one section", () => {
  const rectangles = assessment.match(/Rectangle\(\)/g) || [];
  assert.equal(
    rectangles.length,
    1,
    "exactly one rule, on the outer stack — no second rule inside a section",
  );
});
