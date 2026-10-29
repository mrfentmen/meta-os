// Node built-in test runner, no dependencies:
//   node --test tests/native-ignis-assessment-observation-description-size.test.mjs
//
// IGNIS-UI-50 (Del UI push, Oct 29): native latest-assessment panel
// observation-description size parity. The web panel renders the
// description inline in the observation <li> (js/app.js), and
// styles.css .observations sets only margin and padding-left, so the
// line inherits the 15px body size — but the native description was a
// plain Text at the default 17pt body size, so it read two points
// larger than the web line while the category (UI-49) and the evidence
// line (UI-48) in the same stacked row already matched their own 15px
// web rules. The fix gives the description a 15pt system font, keeping
// the stacked row layout. No Swift toolchain exists in this sandbox,
// so these are static checks on the shipped Swift.

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
const descriptionBlock = observationsFn.slice(
  observationsFn.indexOf("Text(observation.description)"),
  observationsFn.indexOf("if !observation.evidence.isEmpty"),
);
assert.ok(descriptionBlock.length > 0, "observation description block exists");

test("native observation description: web contract — inline text in a 15px observation line", () => {
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
    /item\.appendChild\(document\.createTextNode\(` — \$\{obs\.description\}/,
    "web observation description is inline text in the observation line",
  );
});

test("native observation description: takes 15pt", () => {
  assert.match(
    descriptionBlock,
    /Text\(observation\.description\)\s+\.font\(\.system\(size: 15\)\)/,
    "observation description takes 15pt",
  );
});

test("native observation description: neighbors untouched", () => {
  assert.match(
    observationsFn,
    /Text\(observation\.category\)\s+\.font\(\.system\(size: 15\)\)\s+\.fontWeight\(\.bold\)/,
    "category keeps its UI-49 15pt bold size",
  );
  assert.match(
    observationsFn,
    /Text\(confidenceText\(observation\.confidence\)\)\s+\.font\(\.caption\)\s+\.foregroundStyle\(\.secondary\)/,
    "confidence caption keeps its caption size and muted color",
  );
  assert.match(
    observationsFn,
    /Text\("Evidence: \\\(observation\.evidence\)"\)\s+\.font\(\.system\(size: 15\)\)\s+\.foregroundStyle\(\.secondary\)/,
    "evidence line keeps its muted color at its UI-48 15pt size",
  );
});

test("native observation description: summary keeps its own 15pt rule", () => {
  assert.match(
    assessment,
    /Text\(response\.assessment\.summary\)\s+\.font\(\.system\(size: 15\)\)/,
    "summary keeps its UI-20 15pt size, distinct from the description change",
  );
});
