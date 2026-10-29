// Node built-in test runner, no dependencies:
//   node --test tests/native-ignis-assessment-subline-size.test.mjs
//
// IGNIS-UI-19 (Del UI push, Oct 29): native latest-assessment panel
// subline size parity. The web panel renders its product name with
// class "assessment-product" and its timestamp with class
// "assessment-time" — both 12.5px — but the native concatenated
// subline used .caption (12pt), so both segments read a half point
// smaller than the web's while the review flag (UI-16) already
// matched its own 12px web rule at 12pt and the processing line
// (UI-15) already matched at 12.5pt. The fix gives the subline a
// 12.5pt system font, keeping its timestamp-first order, the
// secondary timestamp, the bold own-accent product segment, and the
// header's single VoiceOver item untouched. No Swift toolchain
// exists in this sandbox, so these are static checks on the shipped
// Swift.

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

const headerFn = assessment.slice(
  assessment.indexOf("private var header"),
  assessment.indexOf("/// Display name for the product key"),
);
assert.ok(headerFn.length > 0, "header exists");
const sublineBlock = headerFn.slice(
  headerFn.indexOf("Text(\"\\(response.timestamp)"),
);
assert.ok(sublineBlock.length > 0, "subline block exists");

test("native subline: 12.5pt system font, segments unchanged", () => {
  assert.match(
    sublineBlock,
    /Text\("\\\(response\.timestamp\) · "\)\s+\.foregroundStyle\(\.secondary\)\s+\+ Text\(productDisplayName\)\s+\.fontWeight\(\.bold\)\s+\.foregroundStyle\(accentColor\)\s+\)\s+\/\/ UI-19[\s\S]*?\.font\(\.system\(size: 12\.5\)\)/,
    "subline keeps secondary timestamp + bold own-accent product, then takes the 12.5pt font",
  );
  assert.doesNotMatch(
    sublineBlock,
    /\.font\(\.caption\)/,
    "subline no longer uses the 12pt caption size",
  );
});

test("native subline: web contract — product and timestamp both 12.5px", () => {
  const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
  assert.match(
    css,
    /\.assessment-product \{\s+color: var\(--accent\);\s+font-size: 12\.5px;\s+font-weight: 700;/,
    "web product name is 12.5px, weight 700, in an accent color",
  );
  assert.match(
    css,
    /\.assessment-time \{\s+color: var\(--muted\);\s+font-size: 12\.5px;/,
    "web timestamp is 12.5px muted",
  );
});

test("native subline: review flag keeps caption, category keeps title3", () => {
  assert.match(
    headerFn,
    /Label\("REQUIRES HUMAN REVIEW", systemImage: "exclamationmark\.triangle\.fill"\)\s+\.font\(\.caption\)/,
    "review flag keeps its 12pt caption size (UI-16)",
  );
  assert.match(
    headerFn,
    /Text\(response\.assessment\.category\)\s+\.font\(\.title3\)/,
    "category keeps its title3 size",
  );
  assert.match(
    headerFn,
    /\.accessibilityElement\(children: \.combine\)/,
    "header stays one VoiceOver item",
  );
});

test("native subline: exactly one plain 12.5pt font, processing line keeps mono", () => {
  const plain = assessment.match(/\.font\(\.system\(size: 12\.5\)\)/g) || [];
  assert.equal(plain.length, 1, "exactly one plain 12.5pt font in the file");
  assert.match(
    assessment,
    /\.font\(\.system\(size: 12\.5, design: \.monospaced\)\)/,
    "processing line keeps its 12.5pt monospace font (UI-15)",
  );
});
