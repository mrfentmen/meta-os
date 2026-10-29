// Node built-in test runner, no dependencies:
//   node --test tests/native-ignis-assessment-padding.test.mjs
//
// IGNIS-UI-11 (Del UI push, Oct 29): native latest-assessment panel
// inner-padding parity. The web .panel carries padding of 14px 16px,
// but the native panel carried no inner inset at all — only the UI-5
// 10pt leading rule gap — so its text sat flush against the top,
// bottom, and trailing card edges while the web panel breathed
// inside its border. The fix insets the outer stack 14pt top/bottom
// and 16pt leading/trailing, before the UI-5 leading padding, so the
// rule overlay still lands on the card's outer edge and the wash,
// clip, border, and shadow still cover the whole card. The leading
// total is therefore 16pt panel inset plus the 10pt rule gap (26pt),
// while top, bottom, and trailing map directly from the CSS pixels.
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

test("native assessment panel: inner padding before the UI-5 rule gap", () => {
  assert.match(
    bodyFn,
    /\.frame\(maxWidth: \.infinity, alignment: \.leading\)[\s\S]*?\.padding\(EdgeInsets\(top: 14, leading: 16, bottom: 14, trailing: 16\)\)[\s\S]*?\.padding\(\.leading, 10\)\s+\.overlay\(alignment: \.leading\) \{\s+Rectangle\(\)\s+\.fill\(accentColor\)\s+\.frame\(width: 3\)/,
    "padding sits on the outer stack after the frame and before the UI-5 leading gap and rule, so the rule stays on the card edge",
  );
  const paddings = bodyFn.match(
    /\.padding\(EdgeInsets\(top: 14, leading: 16, bottom: 14, trailing: 16\)\)/g,
  ) || [];
  assert.equal(paddings.length, 1, "exactly one panel inner padding");
});

test("native assessment panel: padding values match the web .panel padding", () => {
  const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
  assert.match(
    css,
    /\.panel \{\s+background: var\(--panel\);\s+border: 1px solid var\(--panel-border\);\s+border-radius: 8px;\s+padding: 14px 16px;/,
    "web .panel padding is 14px vertical, 16px horizontal",
  );
  assert.match(
    bodyFn,
    /\.padding\(EdgeInsets\(top: 14, leading: 16, bottom: 14, trailing: 16\)\)/,
    "native padding is 14pt top/bottom, 16pt leading/trailing",
  );
});

test("native assessment panel: padding adds no second rule, wash, clip, border, or shadow", () => {
  const rectangles = bodyFn.match(/Rectangle\(\)/g) || [];
  assert.equal(
    rectangles.length,
    1,
    "exactly one Rectangle — the UI-5 rule; the padding is not a second rule",
  );
  const washes = bodyFn.match(/\.background\(accentColor\.opacity\(0\.09\)\)/g) || [];
  assert.equal(washes.length, 1, "exactly one panel wash — the UI-6 wash");
  const clips = bodyFn.match(/\.clipShape\(RoundedRectangle\(cornerRadius: 8\)\)/g) || [];
  assert.equal(clips.length, 1, "exactly one panel clip — the UI-7 clip");
  const strokes = bodyFn.match(/\.stroke\(accentColor\.opacity\(0\.5\), lineWidth: 1\)/g) || [];
  assert.equal(strokes.length, 1, "exactly one panel border stroke — the UI-9 border");
  const shadows = bodyFn.match(
    /\.shadow\(color: \.black\.opacity\(0\.35\), radius: 12, x: 0, y: 8\)/g,
  ) || [];
  assert.equal(shadows.length, 1, "exactly one panel drop shadow — the UI-10 shadow");
});

test("native assessment panel: padding tracks no accent and no selected product", () => {
  assert.doesNotMatch(
    bodyFn,
    /\.padding\(EdgeInsets\([^)]*accentColor/,
    "padding is a fixed inset, not the assessment accent",
  );
  assert.doesNotMatch(
    assessment,
    /selectedProduct/,
    "AssessmentView never consults the selected product",
  );
});
