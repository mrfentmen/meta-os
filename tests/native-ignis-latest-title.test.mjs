// Node built-in test runner, no dependencies:
//   node --test tests/native-ignis-latest-title.test.mjs
//
// IGNIS-UI-22 (Del UI push, Oct 29): native Latest-panel title size
// parity. The web Latest panel renders its title as a .panel h2 —
// styles.css sets .panel h2 at 15px weight 700, and index.html gives
// the Latest section that h2 — but the native panel's title used
// .headline (17pt semibold), so it read larger and one step lighter
// than the web title while the notes below it (UI-21, 13pt) already
// matched their own web rule. The fix gives the title a 15pt bold
// system font, keeping its wording, header trait, and column
// spacing. No Swift toolchain exists in this sandbox, so these are
// static checks on the shipped Swift.

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

const rightColumn = content.slice(
  content.indexOf("private var rightColumn"),
  content.indexOf("TimelineView(model: model)"),
);
assert.ok(rightColumn.length > 0, "rightColumn exists");

test("native latest title: web contract — .panel h2 at 15px weight 700", () => {
  const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
  assert.match(
    css,
    /\.panel h2 \{\s+margin: 0 0 10px;\s+font-size: 15px;\s+font-weight: 700;/,
    "web .panel h2 is 15px weight 700",
  );
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.match(
    html,
    /<section class="panel" aria-label="Latest assessment">\s+<h2>Latest assessment<\/h2>/,
    "web Latest section carries the h2 title",
  );
});

test("native latest title: PanelHeading with Ignis gate, header trait kept", () => {
  // OPS-CONSOLE-2 moved the title into the shared PanelHeading; the
  // 15pt bold itself now lives in PanelHeading's non-Ignis branch
  // (covered by native-ignis-ops-console-headings), and this test
  // keeps the call-site wiring: the Ignis gate and the header trait.
  assert.match(
    rightColumn,
    /\/\/ UI-22[\s\S]*?PanelHeading\(title: "Latest assessment", isIgnis: model\.selectedProduct == \.ignis, isVigiles: model\.selectedProduct == \.vigiles, isMedicus: model\.selectedProduct == \.medicus\)\s+\.accessibilityAddTraits\(\.isHeader\)/,
    "Latest title uses PanelHeading gated on Ignis, keeping its header trait",
  );
});

test("native latest title: no headline font left in the Latest panel", () => {
  const headlines = rightColumn.match(/\.font\(\.headline\)/g) || [];
  assert.equal(headlines.length, 0, "no headline font left in rightColumn");
});
