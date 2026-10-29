// Node built-in test runner, no dependencies:
//   node --test tests/native-ignis-assessment-corners.test.mjs
//
// IGNIS-UI-7 (Del UI push, Oct 29): native latest-assessment panel
// rounded-corner parity. The web .panel is an 8px rounded card, and
// the native panel carries the UI-5 3pt leading rule plus the UI-6
// 0.09 accent wash, but nothing rounded the native panel itself, so
// the wash and the rule ran square to the panel boundary while the
// web panel cut them to a rounded edge. The fix clips the outer
// stack to a RoundedRectangle of radius 8 after the wash. No Swift
// toolchain exists in this sandbox, so these are static checks on
// the shipped Swift.

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

const bodyFn = assessment.slice(assessment.indexOf("var body: some View"));
assert.ok(bodyFn.length > 0, "body exists");

test("native assessment panel: outer stack is clipped to an 8px rounded rectangle after the wash", () => {
  assert.match(
    bodyFn,
    /\.background\(accentColor\.opacity\(0\.09\)\)[\s\S]*?\.clipShape\(RoundedRectangle\(cornerRadius: 8\)\)/,
    "clip sits on the outer stack after the UI-6 wash, so the wash and the UI-5 rule share the rounded edge",
  );
  const clips = bodyFn.match(/\.clipShape\(RoundedRectangle\(cornerRadius: 8\)\)/g) || [];
  assert.equal(clips.length, 1, "exactly one panel clip");
});

test("native assessment panel: clip radius matches the web panel radius", () => {
  const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
  const panel = css.match(/\.panel \{[^}]*\}/);
  assert.ok(panel, "web .panel rule exists");
  assert.match(panel[0], /border-radius: 8px/, "web panel radius is 8px");
  assert.match(
    bodyFn,
    /\.clipShape\(RoundedRectangle\(cornerRadius: 8\)\)/,
    "native clip radius is 8, matching the web panel",
  );
});

test("native assessment panel: rounded corners add no second rule or wash", () => {
  const rectangles = bodyFn.match(/Rectangle\(\)/g) || [];
  assert.equal(
    rectangles.length,
    1,
    "exactly one Rectangle — the UI-5 rule; the clip rounds it, it does not add an edge",
  );
  const washes = bodyFn.match(/\.background\(accentColor\.opacity\(0\.09\)\)/g) || [];
  assert.equal(washes.length, 1, "exactly one panel wash — the UI-6 wash");
});

test("native assessment panel: clip changes no accent source", () => {
  assert.doesNotMatch(
    assessment,
    /selectedProduct/,
    "AssessmentView never consults the selected product",
  );
  const helper = assessment.slice(assessment.indexOf("private var accentColor"));
  assert.ok(helper.length > 0, "accentColor helper exists");
  assert.match(
    helper,
    /switch ProductID\(rawValue: response\.product\)\?\.config\.accentColorName/,
    "rule and wash still track the assessment's own product",
  );
});
