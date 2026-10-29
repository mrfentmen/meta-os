// Node built-in test runner, no dependencies:
//   node --test tests/native-ignis-assessment-observation-confidence-size.test.mjs
//
// IGNIS-UI-51 (Del UI push, Oct 29): native latest-assessment panel
// observation-confidence size parity. The web panel renders the
// confidence inside the parenthetical in the observation <li>
// (js/app.js), and styles.css .observations sets only margin and
// padding-left, so the line inherits the 15px body size — but the
// native confidence was a .caption Text (12pt), so it read three
// points smaller than the web line while the category (UI-49), the
// description (UI-50), and the evidence line (UI-48) in the same row
// already matched their own 15px web rules. The fix gives the
// confidence a 15pt system font, keeping its muted color and wording.
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

const observationsFn = assessment.slice(
  assessment.indexOf("private var observationsSection"),
  assessment.indexOf("private var uncertaintySection"),
);
assert.ok(observationsFn.length > 0, "observations section exists");
const confidenceBlock = observationsFn.slice(
  observationsFn.indexOf("Text(confidenceText(observation.confidence))"),
  observationsFn.indexOf("Text(observation.description)"),
);
assert.ok(confidenceBlock.length > 0, "observation confidence block exists");

test("native observation confidence: web contract — inside the parenthetical of a 15px observation line", () => {
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
    /const confidence = obs\.confidence === null \? "confidence: not reported" : `confidence: \$\{obs\.confidence\.toFixed\(2\)\}`;/,
    "web observation confidence is a labeled value in the observation line",
  );
  assert.match(
    renderLatest,
    /item\.appendChild\(document\.createTextNode\(` — \$\{obs\.description\} \(\$\{evidencePart\}\$\{confidence\}\)`\)\);/,
    "web observation confidence sits inside the observation line's parenthetical",
  );
});

test("native observation confidence: takes 15pt, keeps muted color", () => {
  assert.match(
    confidenceBlock,
    /Text\(confidenceText\(observation\.confidence\)\)\s+\.font\(\.system\(size: 15\)\)\s+\.foregroundStyle\(\.secondary\)/,
    "observation confidence takes 15pt and keeps its muted color",
  );
});

test("native observation confidence: neighbors untouched", () => {
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
    /Text\("Evidence: \\\(observation\.evidence\)"\)\s+\.font\(\.system\(size: 15\)\)\s+\.foregroundStyle\(\.secondary\)/,
    "evidence line keeps its muted color at its UI-48 15pt size",
  );
});

test("native observation confidence: header category keeps its own 20pt rule", () => {
  assert.match(
    assessment,
    /Text\(response\.assessment\.category\)\s+\.font\(\.title3\)\s+\.fontWeight\(\.bold\)/,
    "header category keeps title3 bold, the counterpart to the web 20px assessment-category rule",
  );
});
