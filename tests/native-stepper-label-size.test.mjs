// Node built-in test runner, no dependencies:
//   node --test tests/native-stepper-label-size.test.mjs
//
// IGNIS-UI-46 (Del UI push, Oct 29): native interval Stepper label size
// parity. The web interval label is styled by the styles.css label rule
// (13px, muted) — the same rule the native endpoint and custom-scenario
// labels already match (UI-33) — but the native Stepper label was a
// plain Text at the default body size, so it read four points larger
// and in full-strength color than the web label while the sampling
// disclosure below it (UI-32) already matched its own 13px web rule.
// The fix gives the Stepper label 13pt and the secondary (muted)
// color, keeping the 1...60 range, the binding, the plural wording,
// and the Stepper control itself. No Swift toolchain exists in this
// sandbox, so these are static checks on the shipped Swift.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const content = readFileSync(
  new URL("../native/Sources/MetaTrio/Views/ContentView.swift", import.meta.url),
  "utf8",
);

function blockAfter(marker, length = 600) {
  const start = content.indexOf(marker);
  assert.ok(start >= 0, `${marker} exists`);
  return content.slice(start, start + length);
}

const stepper = blockAfter("Stepper(value: $model.intervalSeconds, in: 1...60)");
const label = blockAfter('Text("Sample one frame every');

test("native stepper label: web contract — label rule at 13px, muted", () => {
  const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
  assert.match(
    css,
    /label \{\s+display: block;\s+margin: 10px 0 4px;\s+font-size: 13px;\s+color: var\(--muted\);/,
    "web label rule is 13px, muted",
  );
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.match(
    html,
    /<label for="interval-seconds">Sampling interval \(seconds, 1–60\)<\/label>/,
    "web interval control carries a label",
  );
});

test("native stepper label: takes 13pt muted, no default size left", () => {
  assert.match(
    label,
    /\.font\(\.system\(size: 13\)\)/,
    "stepper label takes 13pt",
  );
  assert.match(
    label,
    /\.foregroundStyle\(\.secondary\)/,
    "stepper label takes the muted secondary color",
  );
});

test("native stepper label: keeps its range, binding, and plural wording", () => {
  assert.match(
    stepper,
    /Stepper\(value: \$model\.intervalSeconds, in: 1\.\.\.60\)/,
    "stepper keeps its 1...60 range and binding",
  );
  assert.match(
    label,
    /second\\\(model\.intervalSeconds == 1 \? "" : "s"\)/,
    "stepper label keeps its plural wording",
  );
});

test("native stepper label: neighbors unchanged (UI-32 disclosure, UI-33 scenario label)", () => {
  const disclosure = blockAfter("Text(\"Analysis uses sampled frames:");
  assert.match(
    disclosure,
    /\.font\(\.system\(size: 13\)\)\s+\.foregroundStyle\(\.secondary\)/,
    "sampling disclosure keeps its 13pt muted style",
  );
  const scenarioLabel = blockAfter('Text("Or a custom scenario label');
  assert.match(
    scenarioLabel,
    /\.font\(\.system\(size: 13\)\)\s+\.foregroundStyle\(\.secondary\)/,
    "custom-scenario label keeps its 13pt muted style",
  );
});
