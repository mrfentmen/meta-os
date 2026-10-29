// Node built-in test runner, no dependencies:
//   node --test tests/native-settings-label-size.test.mjs
//
// IGNIS-UI-33 (Del UI push, Oct 29): native Settings panel field-label
// size parity. The web frontend carries its settings labels as <label>
// elements — styles.css sets label at 13px in --muted — but the native
// Settings panel's equivalent labels (assessment endpoint, custom
// scenario) used .caption (12pt), so they read one point smaller than
// the web labels while the backend-health and sampling-disclosure
// lines (UI-32) already matched their own 13px web rules. The fix
// gives both labels a 13pt system font, keeping their muted color and
// their wording. No Swift toolchain exists in this sandbox, so these
// are static checks on the shipped Swift.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const content = readFileSync(
  new URL(
    "../native/Sources/MetaTrio/Views/ContentView.swift",
    import.meta.url,
  ),
  "utf8",
);

function blockAfter(marker, length = 400) {
  const start = content.indexOf(marker);
  assert.ok(start >= 0, `${marker} exists`);
  return content.slice(start, start + length);
}

const endpoint = blockAfter('Text("Assessment endpoint")');
const scenario = blockAfter(
  'Text("Or a custom scenario label (overrides the choice above)")',
  500,
);

test("native settings labels: web contract — label at 13px muted", () => {
  const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
  assert.match(
    css,
    /label \{\s+display: block;\s+margin: 10px 0 4px;\s+font-size: 13px;\s+color: var\(--muted\);/,
    "web label is 13px muted",
  );
});

test("native settings labels: web labels exist for both fields", () => {
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.match(
    html,
    /<label for="endpoint">Assessment endpoint<\/label>/,
    "web endpoint label exists",
  );
  assert.match(
    html,
    /<label for="scenario-label">Or a custom scenario label \(overrides the choice above\)<\/label>/,
    "web scenario label exists",
  );
});

test("native settings labels: endpoint label takes 13pt", () => {
  assert.match(endpoint, /\.font\(\.system\(size: 13\)\)/, "endpoint label takes 13pt");
  assert.doesNotMatch(endpoint, /\.font\(\.caption\)/, "no caption left on endpoint label");
  assert.match(endpoint, /\.foregroundStyle\(\.secondary\)/, "endpoint label keeps muted color");
});

test("native settings labels: custom-scenario label takes 13pt", () => {
  assert.match(scenario, /\.font\(\.system\(size: 13\)\)/, "scenario label takes 13pt");
  assert.doesNotMatch(scenario, /\.font\(\.caption\)/, "no caption left on scenario label");
  assert.match(scenario, /\.foregroundStyle\(\.secondary\)/, "scenario label keeps muted color");
});
