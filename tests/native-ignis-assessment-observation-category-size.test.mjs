// Node built-in test runner, no dependencies:
//   node --test tests/native-ignis-assessment-observation-category-size.test.mjs
//
// IGNIS-UI-49 (Del UI push, Oct 29): native latest-assessment panel
// observation-category size parity. The web panel renders the category
// as the strong element opening the observation <li> (js/app.js), and
// styles.css .observations sets only margin and padding-left, so the
// line inherits the 15px body size — but the native category was a
// plain bold Text at the default 17pt body size, so it read two points
// larger than the web category while the evidence line (UI-48) already
// matched its own 15px web rule. The fix gives the category a 15pt
// system font, keeping its bold weight. No Swift toolchain exists in
// this sandbox, so these are static checks on the shipped Swift.

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
const categoryBlock = observationsFn.slice(
  observationsFn.indexOf("Text(observation.category)"),
  observationsFn.indexOf("Spacer()"),
);
assert.ok(categoryBlock.length > 0, "observation category block exists");

test("native observation category: web contract — strong element in a 15px observation line", () => {
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
    /const category = document\.createElement\("strong"\);\s+category\.textContent = obs\.category;/,
    "web observation category is a strong element in the observation line",
  );
});

test("native observation category: takes 15pt, keeps bold weight", () => {
  assert.match(
    categoryBlock,
    /Text\(observation\.category\)\s+\.font\(\.system\(size: 15\)\)\s+\.fontWeight\(\.bold\)/,
    "observation category takes 15pt and keeps its bold weight",
  );
});

test("native observation category: neighbors untouched", () => {
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

test("native observation category: header category keeps its own 20pt rule", () => {
  assert.match(
    assessment,
    /Text\(response\.assessment\.category\)\s+\.font\(\.title3\)\s+\.fontWeight\(\.bold\)/,
    "header category keeps title3 bold, the counterpart to the web 20px assessment-category rule",
  );
});
