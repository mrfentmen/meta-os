// Node built-in test runner, no dependencies:
//   node --test tests/latest-processing-line.test.mjs
//
// HANA Agent1: the Latest assessment panel's processing line — the
// web counterpart to the native AssessmentView processingLine, which
// reads "Model: … · Server-reported latency: …" with the latency as
// a whole number when it is one and one decimal otherwise (the native
// serverLatencyText rule). The web line said "server latency" and
// interpolated the raw number, so a fractional latency printed at
// full precision, and the wording did not say whose latency it was:
// the panel also shows a client-measured round trip elsewhere, so the
// old wording could be read as that round trip. "Server-reported"
// names the source exactly, like the native line. A null latency
// still reads "not reported", never invented. No Swift toolchain
// exists in this sandbox, so these are static checks on the shipped
// web sources and the shipped Swift.

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

test("web: Latest panel processing line names the latency server-reported", () => {
  assert.match(
    render,
    /Server-reported latency:/,
    "processing line uses the native Server-reported latency wording",
  );
  assert.doesNotMatch(
    render,
    /· server latency:/,
    "old ambiguous wording is gone",
  );
  assert.match(
    render,
    /const processing = document\.createElement\("p"\);/,
    "processing line is still one paragraph",
  );
});

test("web: Latest panel latency formats whole or one decimal, null stays not reported", () => {
  assert.match(
    render,
    /latencyMs === null\s+\? "not reported"/,
    "null latency still reads not reported",
  );
  assert.match(
    render,
    /Number\.isInteger\(latencyMs\)/,
    "whole latencies print without a decimal",
  );
  assert.match(
    render,
    /latencyMs\.toFixed\(1\)/,
    "fractional latencies print at one decimal, like the native %.1f rule",
  );
});

test("native: AssessmentView processing line still matches the web wording and format", () => {
  assert.match(
    native,
    /Text\("Model: \\\(response\.processing\.model\) · Server-reported latency: \\\(serverLatencyText\)"\)/,
    "native processing line keeps the Server-reported latency wording",
  );
  assert.match(
    native,
    /if latency == latency\.rounded\(\) \{\s+return "\\\(Int\(latency\)\) ms"/,
    "native whole latencies still print as integers",
  );
  assert.match(
    native,
    /String\(format: "%.1f ms", latency\)/,
    "native fractional latencies still print at one decimal",
  );
});
