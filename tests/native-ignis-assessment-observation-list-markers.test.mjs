// Node built-in test runner, no dependencies:
//   node --test tests/native-ignis-assessment-observation-list-markers.test.mjs
//
// IGNIS-UI-18 (Del UI push, Oct 29): native latest-assessment panel
// observation-list bullet and inset parity. The web panel renders its
// observations as a <ul> with class "observations" — padding-left
// 18px and default disc markers — but the native rows sat flush left
// with no marker, so a populated list read as loose stacked blocks
// while the web list read as an indented bulleted list. The fix puts
// 18pt of leading padding on each native row and seats a bullet in
// that padding box via a topLeading overlay, the same outside
// position the web disc occupies, instead of pushing the text further
// right as a leading HStack glyph would. The bullet is visual-only
// (accessibilityHidden, like a web list marker). No Swift toolchain
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

const observationsFn = assessment.slice(
  assessment.indexOf("private var observationsSection"),
  assessment.indexOf("private var uncertaintySection"),
);
assert.ok(observationsFn.length > 0, "observations section exists");
const uncertaintyFn = assessment.slice(
  assessment.indexOf("private var uncertaintySection"),
  assessment.indexOf("private var processingLine"),
);
assert.ok(uncertaintyFn.length > 0, "uncertainty section exists");

test("native observation rows: 18pt leading inset, topLeading overlay bullet, hidden from VoiceOver", () => {
  assert.match(
    observationsFn,
    /\.padding\(\.leading, 18\)\s+\.overlay\(alignment: \.topLeading\) \{\s+[\s\S]*?Text\("•"\)\s+\.font\(\.system\(size: 15\)\)\s+\.accessibilityHidden\(true\)\s+\}/,
    "row carries 18pt leading padding and a hidden 15pt topLeading bullet overlay",
  );
});

test("web observations list: <ul> with padding-left 18px", () => {
  const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
  assert.match(
    css,
    /\.observations \{\s+margin: 6px 0;\s+padding-left: 18px;/,
    "web .observations is margin 6px 0, padding-left 18px",
  );
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  assert.match(
    app,
    /const list = document\.createElement\("ul"\);\s+list\.className = "observations";/,
    "web observations render as a <ul> with class observations",
  );
});

test("native observation rows: content styles unchanged (UI-17 category, confidence, evidence)", () => {
  assert.match(
    observationsFn,
    /Text\(observation\.category\)\s+\.font\(\.system\(size: 15\)\)\s+\.fontWeight\(\.bold\)/,
    "category keeps its UI-17 bold weight at its UI-49 15pt size",
  );
  assert.match(
    observationsFn,
    /Text\(confidenceText\(observation\.confidence\)\)\s+\.font\(\.system\(size: 15\)\)\s+\.foregroundStyle\(\.secondary\)/,
    "confidence keeps its muted color at its UI-51 15pt size",
  );
  assert.match(
    observationsFn,
    /Text\("Evidence: /,
    "evidence line keeps its Evidence label",
  );
  assert.match(
    observationsFn,
    /\.font\(\.system\(size: 15\)\)\s+\.foregroundStyle\(\.secondary\)/,
    "evidence keeps its secondary style at its UI-48 15pt size",
  );
  assert.match(
    observationsFn,
    /Text\("Observations"\)\s+\.font\(\.headline\)\s+\.accessibilityAddTraits\(\.isHeader\)/,
    "Observations heading keeps its headline header style",
  );
});

test("native observation rows: exactly one list inset, uncertainty bullets untouched", () => {
  const insets = assessment.match(/\.padding\(\.leading, 18\)/g) || [];
  assert.equal(insets.length, 1, "exactly one 18pt leading inset in the file");
  const overlays = observationsFn.match(
    /\.overlay\(alignment: \.topLeading\)/g,
  ) || [];
  assert.equal(overlays.length, 1, "exactly one topLeading bullet overlay");
  assert.doesNotMatch(
    uncertaintyFn,
    /\.padding\(\.leading, 18\)/,
    "uncertainty section gains no 18pt inset",
  );
  assert.doesNotMatch(
    uncertaintyFn,
    /\.overlay\(alignment: \.topLeading\)/,
    "uncertainty section gains no overlay bullet",
  );
  assert.match(
    uncertaintyFn,
    /HStack\(alignment: \.top, spacing: 6\) \{\s+Text\("•"\)/,
    "uncertainty keeps its own UI-14 HStack bullet",
  );
});
