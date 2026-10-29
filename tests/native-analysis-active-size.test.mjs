// Node built-in test runner, no dependencies:
//   node --test tests/native-analysis-active-size.test.mjs
//
// IGNIS-UI-45 (Del UI push, Oct 29): native ANALYSIS ACTIVE size parity.
// The web line is #analysis-active with class .note (13px), but the
// native camera panel's ANALYSIS ACTIVE banner used .caption (12pt),
// so it read one point smaller than the web line it mirrors while
// the camera state lines (UI-35) and the facing and guidance notes
// (UI-28, UI-29) already matched their own 13px web rules. The fix
// gives the banner 13pt, keeping its bold weight, orange indicator
// color, icon, wording, and accessibility label. No Swift toolchain
// exists in this sandbox, so these are static checks on the shipped
// Swift.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const content = readFileSync(
  new URL("../native/Sources/MetaTrio/Views/ContentView.swift", import.meta.url),
  "utf8",
);

const start = content.indexOf('Label("ANALYSIS ACTIVE');
assert.ok(start >= 0, "ANALYSIS ACTIVE banner exists");
const banner = content.slice(start, start + 600);

test("native analysis-active: web contract — #analysis-active carries .note at 13px", () => {
  const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
  assert.match(
    css,
    /\.note \{\s+color: var\(--muted\);\s+font-size: 13px;\s+\}/,
    "web .note is 13px",
  );
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.ok(
    html.includes('<p id="analysis-active" class="note"'),
    "web analysis-active line carries .note",
  );
});

test("native analysis-active: banner takes 13pt, no caption left", () => {
  assert.match(banner, /\.font\(\.system\(size: 13\)\)/, "banner takes 13pt");
  assert.doesNotMatch(banner, /\.font\(\.caption\)/, "no caption on banner");
});

test("native analysis-active: keeps its weight, color, icon, wording, and label", () => {
  assert.match(banner, /\.fontWeight\(\.bold\)/, "banner keeps its bold weight");
  assert.match(
    banner,
    /\.foregroundStyle\(\.orange\)/,
    "banner keeps its orange indicator color",
  );
  assert.ok(
    banner.includes('systemImage: "dot.radiowaves.left.and.right"'),
    "banner keeps its icon",
  );
  assert.ok(
    banner.includes("ANALYSIS ACTIVE — sampling one frame every"),
    "banner keeps its wording",
  );
  assert.ok(
    banner.includes(
      '.accessibilityLabel("Analysis active, sampling one frame every \\(model.intervalSeconds) seconds")',
    ),
    "banner keeps its accessibility label",
  );
});
