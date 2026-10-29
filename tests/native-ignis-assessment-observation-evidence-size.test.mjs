// Node built-in test runner, no dependencies:
//   node --test tests/native-ignis-assessment-observation-evidence-size.test.mjs
//
// IGNIS-UI-48 (Del UI push, Oct 29): native latest-assessment panel
// observation-evidence size parity. The web panel renders evidence
// inline in the observation <li> (js/app.js appends the evidence
// string to the list item's text), and styles.css .observations sets
// only margin and padding-left, so the line inherits the 15px body
// size — but the native evidence line used .callout (16pt), so it
// read one point larger than the web line it comes from while the
// summary (UI-20) and the timeline row detail (UI-43) already matched
// their own 15px web rules. The fix gives the evidence line a 15pt
// system font, keeping its "Evidence: " label, its muted color, and
// its non-empty guard. No Swift toolchain exists in this sandbox, so
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
const evidenceBlock = observationsFn.slice(
  observationsFn.indexOf('Text("Evidence: '),
);
assert.ok(evidenceBlock.length > 0, "evidence line exists");

test("native observation evidence: web contract — observation line at 15px body size", () => {
  const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
  assert.match(
    css,
    /body \{\s+margin: 0;\s+background: var\(--bg\);\s+color: var\(--text\);\s+font-family: [^;]+;\s+font-size: 15px;/,
    "web body is 15px",
  );
  assert.match(
    css,
    /\.observations \{\s+margin: 6px 0;\s+padding-left: 18px;\s+\}/,
    "web .observations sets no font-size of its own, so the line inherits 15px",
  );
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  const renderLatest = app.slice(
    app.indexOf("function renderLatest"),
    app.indexOf("function addHistoryItem"),
  );
  assert.ok(renderLatest.length > 0, "renderLatest exists");
  assert.match(
    renderLatest,
    /const evidencePart = obs\.evidence !== "" \? `\$\{obs\.evidence\}; ` : "";/,
    "web renders evidence inline in the observation list item",
  );
});

test("native observation evidence: takes 15pt, no callout left in the section", () => {
  assert.match(
    evidenceBlock,
    /\.font\(\.system\(size: 15\)\)\s+\.foregroundStyle\(\.secondary\)/,
    "evidence line takes 15pt and keeps its muted color",
  );
  assert.doesNotMatch(
    observationsFn,
    /\.font\(\.callout\)/,
    "no callout left in the observations section",
  );
});

test("native observation evidence: keeps its label and non-empty guard", () => {
  assert.match(
    observationsFn,
    /if !observation\.evidence\.isEmpty \{\s+[^}]*Text\("Evidence: \\\(observation\.evidence\)"\)/,
    "evidence line keeps its non-empty guard and Evidence label",
  );
});

test("native observation evidence: neighbors untouched", () => {
  assert.match(
    observationsFn,
    /Text\(confidenceText\(observation\.confidence\)\)\s+\.font\(\.caption\)\s+\.foregroundStyle\(\.secondary\)/,
    "confidence caption keeps its caption size and muted color",
  );
  assert.match(
    observationsFn,
    /Text\(observation\.category\)\s+\.font\(\.system\(size: 15\)\)\s+\.fontWeight\(\.bold\)/,
    "observation category keeps its bold weight at its UI-49 15pt size",
  );
});
