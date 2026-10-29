// Node built-in test runner, no dependencies:
//   node --test tests/native-ignis-assessment-processing-mono.test.mjs
//
// IGNIS-UI-15 (Del UI push, Oct 29): native latest-assessment panel
// processing-line mono parity. The web panel renders its processing
// line with class "note mono" — muted, 12.5px, ui-monospace stack —
// but the native line used .caption (12pt proportional system text)
// while already muted, so it read as ordinary body copy instead of
// the web's small monospace status line. The fix gives the native
// line a 12.5pt monospaced face, keeping its muted color and its
// Server-reported latency wording untouched. No Swift toolchain
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

const processingFn = assessment.slice(
  assessment.indexOf("private var processingLine"),
  assessment.indexOf("private var serverLatencyText"),
);
assert.ok(processingFn.length > 0, "processingLine exists");

test("native processing line: 12.5pt monospaced face, still muted", () => {
  assert.match(
    processingFn,
    /Model: .*Server-reported latency:/,
    "processing line keeps its Model / Server-reported latency text",
  );
  assert.match(
    processingFn,
    /\.font\(\.system\(size: 12\.5, design: \.monospaced\)\)\s+\.foregroundStyle\(\.secondary\)/,
    "processing line carries .font(.system(size: 12.5, design: .monospaced)) and stays muted",
  );
  assert.doesNotMatch(
    processingFn,
    /\.font\(\.caption\)/,
    "processing line no longer uses proportional .caption",
  );
});

test("native processing line: web line is note mono, 12.5px monospace", () => {
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  assert.match(
    app,
    /processing\.className = "note mono";/,
    "web processing line carries the note mono classes",
  );
  const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
  assert.match(
    css,
    /\.mono \{\s+font-family: var\(--mono\);\s+font-size: 12\.5px;/,
    "web .mono is the 12.5px monospace rule",
  );
  assert.match(
    css,
    /\.note \{\s+color: var\(--muted\);/,
    "web .note is muted",
  );
});

test("native processing line: wording and muted color unchanged, no accent", () => {
  assert.match(
    processingFn,
    /Server-reported latency:/,
    "processing line keeps the Server-reported latency wording",
  );
  assert.doesNotMatch(
    processingFn,
    /accentColor/,
    "processing line tracks no product accent",
  );
});

test("native processing line: exactly one mono face, other sections untouched", () => {
  const monoFaces =
    assessment.match(/design: \.monospaced/g) || [];
  assert.equal(monoFaces.length, 1, "exactly one monospaced face in the file");
  const observationsFn = assessment.slice(
    assessment.indexOf("private var observationsSection"),
    assessment.indexOf("private var uncertaintySection"),
  );
  assert.doesNotMatch(
    observationsFn,
    /monospaced/,
    "observations gain no mono face",
  );
  const uncertaintyFn = assessment.slice(
    assessment.indexOf("private var uncertaintySection"),
    assessment.indexOf("private var processingLine"),
  );
  assert.doesNotMatch(
    uncertaintyFn,
    /monospaced/,
    "uncertainty gains no mono face",
  );
});
