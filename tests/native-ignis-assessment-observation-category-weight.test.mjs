// Node built-in test runner, no dependencies:
//   node --test tests/native-ignis-assessment-observation-category-weight.test.mjs
//
// IGNIS-UI-17 (Del UI push, Oct 29): native latest-assessment panel
// observation-category weight parity. The web panel renders each
// observation's category with a strong element (weight 700), but the
// native row used semibold (600), so the category read one step
// lighter than the web's while the header category already matched
// at bold. The fix moves the native observation category to bold,
// keeping the confidence caption, description, and evidence lines
// untouched. No Swift toolchain exists in this sandbox, so these are
// static checks on the shipped Swift.

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

const observationsFn = assessment.slice(
  assessment.indexOf("private var observationsSection"),
  assessment.indexOf("private var uncertaintySection"),
);
assert.ok(observationsFn.length > 0, "observations section exists");
const categoryBlock = observationsFn.slice(
  observationsFn.indexOf("Text(observation.category)"),
  observationsFn.indexOf("Spacer()"),
);
assert.ok(categoryBlock.length > 0, "observation category block exists");

test("native observation category: bold weight, matching web strong", () => {
  assert.match(
    categoryBlock,
    /Text\(observation\.category\)\s+\.fontWeight\(\.bold\)/,
    "observation category is bold",
  );
});

test("web observation category: strong element in the Latest panel", () => {
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  const renderLatest = app.slice(
    app.indexOf("function renderLatest"),
    app.indexOf("function addHistoryItem"),
  );
  assert.ok(renderLatest.length > 0, "renderLatest exists");
  assert.match(
    renderLatest,
    /const category = document\.createElement\("strong"\);\s+category\.textContent = obs\.category;/,
    "web observation category is a strong element",
  );
});

test("native observation category: no semibold left in the panel, neighbors untouched", () => {
  assert.doesNotMatch(
    assessment,
    /\.fontWeight\(\.semibold\)/,
    "no semibold weight remains in AssessmentView",
  );
  assert.match(
    observationsFn,
    /Text\(confidenceText\(observation\.confidence\)\)\s+\.font\(\.caption\)\s+\.foregroundStyle\(\.secondary\)/,
    "confidence caption keeps its caption size and muted color",
  );
  assert.match(
    observationsFn,
    /Text\("Evidence: \\\(observation\.evidence\)"\)\s+\.font\(\.callout\)\s+\.foregroundStyle\(\.secondary\)/,
    "evidence line keeps its callout size and muted color",
  );
});
