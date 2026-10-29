// Node built-in test runner, no dependencies:
//   node --test tests/native-ignis-assessment-shadow.test.mjs
//
// IGNIS-UI-10 (Del UI push, Oct 29): native latest-assessment panel
// drop-shadow parity. The web theme panels carry a box-shadow of
// 0 0 0 1px rgba(accent, 0.15), 0 8px 24px rgba(0, 0, 0, 0.35), but
// the native panel cast no shadow at all, so under Ignis or Sanitas
// it read flat while the web panel lifted off the page. The fix
// shadows the outer stack black at 0.35, 8pt down, radius 12, after
// the UI-9 border overlay. The 1px 0.15 ring is deliberately not
// mirrored: the UI-9 stroke already draws a stronger 1pt accent edge
// at 0.5, so a second faint ring would double the edge. The radius
// is an approximation, stated plainly: a CSS blur of 24px spreads
// roughly twice as far as a SwiftUI shadow radius unit, so 12
// approximates the web spread while the 8pt offset and 0.35 strength
// map directly. The shadow is product-neutral black, exactly like
// the web shadow, so it tracks no accent.
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

test("native assessment panel: drop shadow after the UI-9 border overlay", () => {
  assert.match(
    bodyFn,
    /\.overlay\(\s*RoundedRectangle\(cornerRadius: 8\)\s*\.stroke\(accentColor\.opacity\(0\.5\), lineWidth: 1\)\s*\)[\s\S]*?\.shadow\(color: \.black\.opacity\(0\.35\), radius: 12, x: 0, y: 8\)/,
    "shadow sits on the outer stack after the border overlay, so the whole bordered card casts it",
  );
  const shadows = bodyFn.match(
    /\.shadow\(color: \.black\.opacity\(0\.35\), radius: 12, x: 0, y: 8\)/g,
  ) || [];
  assert.equal(shadows.length, 1, "exactly one panel drop shadow");
});

test("native assessment panel: shadow strength matches the web theme drop shadow", () => {
  const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
  assert.match(
    css,
    /body\[data-product="ignis"\] \.panel \{[^}]*box-shadow: 0 0 0 1px rgba\(217, 43, 43, 0\.15\), 0 8px 24px rgba\(0, 0, 0, 0\.35\)/,
    "web Ignis panel shadow is 0 8px 24px rgba(0, 0, 0, 0.35)",
  );
  assert.match(
    css,
    /body\[data-product="sanitas"\] \.panel \{[^}]*box-shadow: 0 0 0 1px rgba\(93, 168, 100, 0\.15\), 0 8px 24px rgba\(0, 0, 0, 0\.35\)/,
    "web Sanitas panel shadow is 0 8px 24px rgba(0, 0, 0, 0.35)",
  );
  assert.match(
    bodyFn,
    /\.shadow\(color: \.black\.opacity\(0\.35\), radius: 12, x: 0, y: 8\)/,
    "native shadow is black at 0.35, 8pt down",
  );
});

test("native assessment panel: shadow adds no second rule, wash, clip, or border", () => {
  const rectangles = bodyFn.match(/Rectangle\(\)/g) || [];
  assert.equal(
    rectangles.length,
    1,
    "exactly one Rectangle — the UI-5 rule; the shadow is not a second rule",
  );
  const washes = bodyFn.match(/\.background\(accentColor\.opacity\(0\.09\)\)/g) || [];
  assert.equal(washes.length, 1, "exactly one panel wash — the UI-6 wash");
  const clips = bodyFn.match(/\.clipShape\(RoundedRectangle\(cornerRadius: 8\)\)/g) || [];
  assert.equal(clips.length, 1, "exactly one panel clip — the UI-7 clip");
  const strokes = bodyFn.match(/\.stroke\(accentColor\.opacity\(0\.5\), lineWidth: 1\)/g) || [];
  assert.equal(strokes.length, 1, "exactly one panel border stroke — the UI-9 border");
});

test("native assessment panel: shadow tracks no accent and no selected product", () => {
  assert.doesNotMatch(
    bodyFn,
    /\.shadow\(color: accentColor/,
    "shadow is product-neutral black, not the assessment accent",
  );
  assert.doesNotMatch(
    assessment,
    /selectedProduct/,
    "AssessmentView never consults the selected product",
  );
});
