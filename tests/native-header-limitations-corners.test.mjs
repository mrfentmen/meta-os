// Node built-in test runner, no dependencies:
//   node --test tests/native-header-limitations-corners.test.mjs
//
// HANA Agent1 UI-8 (Oct 29): native header limitations box
// rounded-corner parity, the counterpart to UI-7's assessment-panel
// clip. The limitations box is a rounded card (its background was
// rounded with cornerRadius(6)), but the R2 accent leading rule is an
// overlay that sits after that modifier, so the rule was never cut to
// the rounded edge and ran square past the box's corners at the
// leading edge, while the UI-7 assessment panel cuts its rule and
// wash to the same rounded edge. The fix clips the whole box to a
// RoundedRectangle of radius 6 after the overlay. No Swift toolchain
// exists in this sandbox, so these are static checks on the shipped
// Swift.
//

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const content = readFileSync(
  new URL("../native/Sources/MetaTrio/Views/ContentView.swift", import.meta.url),
  "utf8",
);

const header = content.slice(
  content.indexOf("private struct HeaderView"),
  content.indexOf("// MARK: - Camera panel"),
);
assert.ok(header.length > 0, "HeaderView section exists");

const limitations = header.slice(header.indexOf("Text(model.config.limitations"));
assert.ok(limitations.length > 0, "limitations text exists");

test("native header limitations box: clipped to a 6px rounded rectangle after the rule overlay", () => {
  assert.match(
    limitations,
    /\.overlay\(alignment: \.leading\) \{[\s\S]*?Rectangle\(\)[\s\S]*?\.fill\(accentColor\)[\s\S]*?\.frame\(width: 3\)[\s\S]*?\}[\s\S]*?\.clipShape\(RoundedRectangle\(cornerRadius: 6\)\)/,
    "clip sits on the box after the R2 rule overlay, so the background and the rule share the rounded edge",
  );
  const clips = limitations.match(/\.clipShape\(RoundedRectangle\(cornerRadius: 6\)\)/g) || [];
  assert.equal(clips.length, 1, "exactly one limitations-box clip");
});

test("native header limitations box: the old background-only rounding is gone, so the clip is the single rounding", () => {
  assert.doesNotMatch(
    limitations,
    /\.cornerRadius\(6\)/,
    "no separate cornerRadius left in the limitations chain — the clip after the overlay is the only rounding",
  );
});

test("native header limitations box: clip changes no rule, color, or content", () => {
  const rectangles = limitations.match(/Rectangle\(\)/g) || [];
  assert.equal(
    rectangles.length,
    1,
    "exactly one Rectangle — the R2 rule; the clip rounds it, it does not add an edge",
  );
  const backgrounds = limitations.match(/\.background\(Color\.secondary\.opacity\(0\.08\)\)/g) || [];
  assert.equal(backgrounds.length, 1, "exactly one box background");
  assert.match(
    limitations,
    /\.fill\(accentColor\)/,
    "rule still uses the selected product's accent, like the web .limitations border-left in --accent",
  );
  assert.match(
    limitations,
    /Text\(model\.config\.limitations\)/,
    "limitations text itself is untouched",
  );
});
