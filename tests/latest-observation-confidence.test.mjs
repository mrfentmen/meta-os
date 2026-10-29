// Node built-in test runner, no dependencies:
//   node --test tests/latest-observation-confidence.test.mjs
//
// HANA Agent1: the Latest assessment panel's observation confidence
// label — the web counterpart to the native AssessmentView
// confidenceText, which reads "confidence: 0.72" and "confidence:
// not reported". The web line read "confidence 0.72" and
// "confidence not reported", so the same value read as a bare label
// on one surface and a labeled value on the other. The fix adds the
// colon only: the web line keeps its single-line layout (the native
// panel shows confidence on its own caption row next to the
// category), the two-decimal format, and the "not reported" wording
// for a null confidence, never invented. No Swift toolchain exists
// in this sandbox, so these are static checks on the shipped web
// sources and the shipped Swift.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
const native = readFileSync(
  new URL(
    "../native/Sources/MetaTrio/Views/AssessmentView.swift",
    import.meta.url,
  ),
  "utf8",
);

const render = app.slice(
  app.indexOf("function renderLatest"),
  app.indexOf("function addHistoryItem"),
);
assert.ok(render.length > 0, "renderLatest exists");

test("web: observation confidence label carries the native colon", () => {
  assert.match(
    render,
    /const confidence = obs\.confidence === null \? "confidence: not reported" : `confidence: \$\{obs\.confidence\.toFixed\(2\)\}`;/,
    "confidence reads 'confidence: …' with a colon, null or valued",
  );
  assert.doesNotMatch(
    render,
    /const confidence = obs\.confidence === null \? "confidence not reported"/,
    "old colon-less null wording is gone from the code line",
  );
  assert.doesNotMatch(
    render,
    /const confidence = [^;]*`confidence \$\{obs\.confidence/,
    "old colon-less valued wording is gone from the code line",
  );
});

test("web: observation line keeps its single-line layout and formats", () => {
  assert.match(
    render,
    /item\.appendChild\(document\.createTextNode\(` — \$\{obs\.description\} \(\$\{evidencePart\}\$\{confidence\}\)`\)\);/,
    "confidence still sits inside the observation's parenthetical line",
  );
  assert.match(
    render,
    /obs\.confidence\.toFixed\(2\)/,
    "valued confidences still print at two decimals",
  );
});

test("native: AssessmentView confidenceText still matches the web wording", () => {
  const fn = native.slice(
    native.indexOf("private func confidenceText"),
    native.indexOf("}", native.indexOf('return String(format: "confidence: %.2f"')),
  );
  assert.match(
    native,
    /return "confidence: not reported"/,
    "native null confidence still reads 'confidence: not reported'",
  );
  assert.match(
    native,
    /return String\(format: "confidence: %\.2f", confidence\)/,
    "native valued confidence still reads 'confidence: %.2f'",
  );
  assert.ok(fn.length > 0, "confidenceText exists");
});
