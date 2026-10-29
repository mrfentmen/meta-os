// Node built-in test runner, no dependencies:
//   node --test tests/native-ignis-assessment-observation-bullet-size.test.mjs
//
// IGNIS-UI-52 (Del UI push, Oct 29): native latest-assessment panel
// observation-bullet size parity. The web panel renders its
// observations as a <ul> with class "observations" (js/app.js), and
// styles.css .observations sets only margin and padding-left, so its
// default disc marker scales with the 15px body size of the line it
// marks — but the native bullet was a plain Text at the default 17pt
// body size, so it read two points larger than the web disc while the
// category (UI-49), the description (UI-50), the confidence (UI-51),
// and the evidence line (UI-48) in the same row already matched their
// own 15px web rules. The fix gives the bullet a 15pt system font,
// keeping its 18pt inset, topLeading position, and hidden-from-
// VoiceOver treatment. No Swift toolchain exists in this sandbox, so
// these are static checks on the shipped Swift.

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
const bulletBlock = observationsFn.slice(
  observationsFn.indexOf(".overlay(alignment: .topLeading)"),
);
assert.ok(bulletBlock.length > 0, "observation bullet overlay exists");

test("native observation bullet: web contract — disc marker on a 15px observation line", () => {
  const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
  assert.match(
    css,
    /body \{\s+margin: 0;\s+background: var\(--bg\);\s+color: var\(--text\);\s+font-family: [^;]+;\s+font-size: 15px;/,
    "web body is 15px",
  );
  assert.match(
    css,
    /\.observations \{\s+margin: 6px 0;\s+padding-left: 18px;\s+\}/,
    "web .observations sets no font-size of its own, so the disc scales with the 15px line",
  );
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  assert.match(
    app,
    /const list = document\.createElement\("ul"\);\s+list\.className = "observations";/,
    "web observations render as a <ul> with class observations, so the marker is the default disc",
  );
});

test("native observation bullet: takes 15pt, keeps its hidden marker treatment", () => {
  assert.match(
    bulletBlock,
    /Text\("•"\)\s+\.font\(\.system\(size: 15\)\)\s+\.accessibilityHidden\(true\)/,
    "observation bullet takes 15pt and stays hidden from VoiceOver",
  );
});

test("native observation bullet: row neighbors untouched", () => {
  assert.match(
    observationsFn,
    /Text\(observation\.category\)\s+\.font\(\.system\(size: 15\)\)\s+\.fontWeight\(\.bold\)/,
    "category keeps its UI-49 15pt bold size",
  );
  assert.match(
    observationsFn,
    /Text\(observation\.description\)\s+\.font\(\.system\(size: 15\)\)/,
    "description keeps its UI-50 15pt size",
  );
  assert.match(
    observationsFn,
    /Text\(confidenceText\(observation\.confidence\)\)\s+\.font\(\.system\(size: 15\)\)\s+\.foregroundStyle\(\.secondary\)/,
    "confidence keeps its muted color at its UI-51 15pt size",
  );
  assert.match(
    observationsFn,
    /Text\("Evidence: \\\(observation\.evidence\)"\)\s+\.font\(\.system\(size: 15\)\)\s+\.foregroundStyle\(\.secondary\)/,
    "evidence line keeps its muted color at its UI-48 15pt size",
  );
  assert.match(
    observationsFn,
    /\.padding\(\.leading, 18\)/,
    "row keeps its UI-18 18pt leading inset",
  );
});

test("native observation bullet: uncertainty bullets untouched", () => {
  const uncertaintyFn = assessment.slice(
    assessment.indexOf("private var uncertaintySection"),
    assessment.indexOf("private var processingLine"),
  );
  assert.ok(uncertaintyFn.length > 0, "uncertainty section exists");
  assert.match(
    uncertaintyFn,
    /HStack\(alignment: \.top, spacing: 6\) \{\s+Text\("•"\)/,
    "uncertainty keeps its own UI-14 HStack bullet",
  );
  assert.doesNotMatch(
    uncertaintyFn,
    /\.overlay\(alignment: \.topLeading\)/,
    "uncertainty section gains no overlay bullet",
  );
});
