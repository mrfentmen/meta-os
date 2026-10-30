// Node built-in test runner, no dependencies:
//   node --test tests/native-ignis-assessment-border.test.mjs
//
// IGNIS-UI-9 (Del UI push, Oct 29): native latest-assessment panel
// border parity. The web theme panels carry an accent border —
// Ignis rgba(217, 43, 43, 0.5) and Medicus rgba(93, 168, 100, 0.5) —
// but the native panel carried no border at all, so under Ignis or
// Medicus it read borderless while the web panel carried the tinted
// edge. The fix strokes the outer stack with the assessment's own
// accent at 0.5, 1pt, on the same 8px rounded rectangle as the UI-7
// clip, after the clip so the full line follows the rounded edge.
// Generalization, stated plainly: the web Vigiles panel carries only
// the neutral panel-border, not an accent border, but the native
// panel already tints Vigiles by its own accent in the UI-5 rule and
// UI-6 wash, so the border follows the panel's own accent for all
// three products rather than adding a second, neutral edge rule.
// No Swift toolchain exists in this sandbox, so these are static
// checks on the shipped Swift.

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

test("native assessment panel: stroked with its own accent at 0.5 after the UI-7 clip", () => {
  assert.match(
    bodyFn,
    /\.clipShape\(RoundedRectangle\(cornerRadius: 8\)\)[\s\S]*?\.overlay\(\s*RoundedRectangle\(cornerRadius: 8\)\s*\.stroke\(accentColor\.opacity\(0\.5\), lineWidth: 1\)\s*\)/,
    "stroke sits on the outer stack after the clip, so the full 1pt line follows the rounded edge",
  );
  const strokes = bodyFn.match(/\.stroke\(accentColor\.opacity\(0\.5\), lineWidth: 1\)/g) || [];
  assert.equal(strokes.length, 1, "exactly one panel border stroke");
});

test("native assessment panel: border strength matches the web theme border-color", () => {
  const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
  assert.match(
    css,
    /body\[data-product="ignis"\] \.panel \{[^}]*border-color: rgba\(217, 43, 43, 0\.5\)/,
    "web Ignis panel border is rgba(217, 43, 43, 0.5)",
  );
  assert.match(
    css,
    /body\[data-product="medicus"\] \.panel \{[^}]*border-color: rgba\(93, 168, 100, 0\.5\)/,
    "web Medicus panel border is rgba(93, 168, 100, 0.5)",
  );
  assert.match(
    bodyFn,
    /\.stroke\(accentColor\.opacity\(0\.5\), lineWidth: 1\)/,
    "native border is the assessment's own accent at 0.5, 1pt",
  );
});

test("native assessment panel: border adds no second rule, wash, or clip", () => {
  const rectangles = bodyFn.match(/Rectangle\(\)/g) || [];
  assert.equal(
    rectangles.length,
    1,
    "exactly one Rectangle — the UI-5 rule; the border is a stroked rounded rectangle, not a second rule",
  );
  const washes = bodyFn.match(/\.background\(accentColor\.opacity\(0\.09\)\)/g) || [];
  assert.equal(washes.length, 1, "exactly one panel wash — the UI-6 wash");
  const clips = bodyFn.match(/\.clipShape\(RoundedRectangle\(cornerRadius: 8\)\)/g) || [];
  assert.equal(clips.length, 1, "exactly one panel clip — the UI-7 clip");
});

test("native assessment panel: border changes no accent source", () => {
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
    "border still tracks the assessment's own product",
  );
});
