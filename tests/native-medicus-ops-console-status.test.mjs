// Node built-in test runner, no dependencies:
//   node --test tests/native-medicus-ops-console-status.test.mjs
//
// OPS-CONSOLE-12 (Del UI direction, Oct 29): native Medicus camera
// status lines mirror the web Medicus status-line rule. The web
// rule reads Medicus .status in mono at 0.02em tracking, but the
// native camera state lines (UI-35) kept only the two-gate
// Ignis/Vigiles treatment from OPS-CONSOLE-9, so Medicus never
// read as a console on the Mac past its panel headings and
// Latest-panel body. The fix widens the gate to Ignis, Vigiles,
// or Medicus — the three share one widened value, exactly as
// OPS-CONSOLE-11 did for the readout frame — giving all seven
// state lines the mono face and 0.26pt tracking (0.02em of 13pt)
// when any console product is selected, and exactly the UI-35
// treatment otherwise. The gate is the selected product (the
// PanelHeading precedent: the camera panel is
// product-contextual, not assessment-owned). Size stays 13pt, the
// muted color stays muted, the error lines stay red, the denied
// and failed lines keep their wrapping, and the wording is
// untouched. The facing note (UI-28), the guidance note (UI-29),
// and the ANALYSIS ACTIVE banner (UI-45) are not status lines and
// gain nothing, and the macOS system buttons keep their own corner
// radius. No Swift toolchain exists in this sandbox, so these are
// static checks on the shipped Swift and CSS.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const contentView = readFileSync(
  new URL("../native/Sources/MetaTrio/Views/ContentView.swift", import.meta.url),
  "utf8",
);

const stateText = contentView.slice(
  contentView.indexOf("private var stateText"),
  contentView.indexOf("// MARK: - Still image panel"),
);
assert.ok(stateText.length > 0, "stateText block exists");

const stateLines = [
  'Text("Camera is off.")',
  'Text("Waiting for camera permission…")',
  'Text("Camera is live. No frames are sent anywhere until analysis is started.")',
  'Text("Camera stopped.")',
  'Text("Camera permission denied.',
  'Text("No camera was found on this Mac.")',
  'Text("Camera error:',
];

function blockAfter(marker, length = 500) {
  const start = stateText.indexOf(marker);
  assert.ok(start >= 0, `${marker} exists in stateText`);
  return stateText.slice(start, start + length);
}

test("native ops-console status: web contract — Medicus status rule still mono at 0.02em", () => {
  const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
  assert.match(
    css,
    /body\[data-product="medicus"\] \.status \{\s+font-family: var\(--mono\);\s+letter-spacing: 0\.02em;/,
    "web Medicus status stays mono at 0.02em tracking",
  );
});

test("native ops-console status: gate reads the selected product, PanelHeading precedent", () => {
  assert.match(
    contentView,
    /private var isMedicusSelected: Bool \{\s+model\.selectedProduct == \.medicus\s+\}/,
    "Medicus gate reads the selected product",
  );
});

test("native ops-console status: all seven state lines take mono at 0.26pt on Ignis, Vigiles, or Medicus, plain 13pt off them", () => {
  for (const line of stateLines) {
    const block = blockAfter(line);
    assert.match(
      block,
      /\.font\(\.system\(size: 13, design: \(isIgnisSelected \|\| isVigilesSelected \|\| isMedicusSelected\) \? \.monospaced : \.default\)\)/,
      `${line} keeps 13pt and gains the conditional mono face`,
    );
    assert.match(
      block,
      /\.tracking\(\(isIgnisSelected \|\| isVigilesSelected \|\| isMedicusSelected\) \? 0\.26 : 0\)/,
      `${line} gains 0.26pt tracking on Ignis, Vigiles, or Medicus, none off them`,
    );
  }
  assert.equal(
    (stateText.match(/design: \(isIgnisSelected \|\| isVigilesSelected \|\| isMedicusSelected\) \? \.monospaced : \.default/g) || []).length,
    7,
    "exactly the seven state lines carry the conditional face",
  );
  assert.equal(
    (stateText.match(/tracking\(\(isIgnisSelected \|\| isVigilesSelected \|\| isMedicusSelected\) \? 0\.26 : 0\)/g) || []).length,
    7,
    "exactly the seven state lines carry the conditional tracking",
  );
});

test("native ops-console status: colors and wrapping untouched, red never becomes a status color", () => {
  for (const line of stateLines.slice(0, 4)) {
    assert.match(
      blockAfter(line),
      /\.foregroundStyle\(\.secondary\)/,
      `${line} keeps its muted color`,
    );
  }
  for (const line of stateLines.slice(4)) {
    assert.match(
      blockAfter(line),
      /\.foregroundStyle\(\.red\)/,
      `${line} keeps its red color`,
    );
  }
  assert.match(
    blockAfter('Text("Camera permission denied.'),
    /\.fixedSize\(horizontal: false, vertical: true\)/,
    "denied line keeps its wrapping",
  );
  assert.match(
    blockAfter('Text("Camera error:'),
    /\.fixedSize\(horizontal: false, vertical: true\)/,
    "failed line keeps its wrapping",
  );
});

test("native ops-console status: neighboring notes and banner gain nothing", () => {
  const facing = contentView.slice(
    contentView.indexOf('Text("A facing is a preference'),
    contentView.indexOf("if model.analysisRunning"),
  );
  assert.match(
    facing,
    /\.font\(\.system\(size: 13\)\)/,
    "facing note keeps its plain UI-28 13pt font",
  );
  assert.doesNotMatch(facing, /isMedicusSelected/, "facing note gains no Medicus treatment");
  const guidance = contentView.slice(
    contentView.indexOf("Text(model.config.inputGuidance)"),
    contentView.indexOf("private var cameraAccessibilityValue"),
  );
  assert.match(
    guidance,
    /\.font\(\.system\(size: 13\)\)/,
    "guidance note keeps its plain UI-29 13pt font",
  );
  assert.doesNotMatch(guidance, /isMedicusSelected/, "guidance note gains no Medicus treatment");
});
