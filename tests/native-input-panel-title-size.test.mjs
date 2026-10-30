// Node built-in test runner, no dependencies:
//   node --test tests/native-input-panel-title-size.test.mjs
//
// IGNIS-UI-36 (Del UI push, Oct 29): native still-image and
// prerecorded-video panel title size parity. The web frontend carries
// every panel title as a .panel h2 at 15px weight 700 — but the native
// Still image and Prerecorded video titles used .headline (17pt
// semibold), so they read larger and one step lighter than the web
// input-panel titles while the Latest panel title (UI-23) and the
// timeline title (UI-34) already matched their own 15px web rules.
// The fix gives both titles a 15pt bold system font, keeping their
// wording. No Swift toolchain exists in this sandbox, so these are
// static checks on the shipped Swift.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const content = readFileSync(
  new URL("../native/Sources/MetaTrio/Views/ContentView.swift", import.meta.url),
  "utf8",
);

function blockAfter(marker, length = 500) {
  const start = content.indexOf(marker);
  assert.ok(start >= 0, `${marker} exists`);
  return content.slice(start, start + length);
}

const stillTitle = blockAfter('PanelHeading(title: "Still image"');
const videoTitle = blockAfter('PanelHeading(title: "Prerecorded video"');

test("native input-panel titles: web contract — .panel h2 at 15px weight 700", () => {
  const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
  assert.match(
    css,
    /\.panel h2 \{\s+margin: 0 0 10px;\s+font-size: 15px;\s+font-weight: 700;/,
    "web .panel h2 is 15px weight 700",
  );
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.match(html, /<h2>Still image<\/h2>/, "web still-image panel has h2 title");
  assert.match(html, /<h2>Prerecorded video<\/h2>/, "web video panel has h2 title");
});

test("native still-image title: PanelHeading with Ignis gate, no headline left", () => {
  // OPS-CONSOLE-2 moved the title into the shared PanelHeading; the
  // 15pt bold itself now lives in PanelHeading's non-Ignis branch
  // (covered by native-ignis-ops-console-headings).
  assert.match(
    stillTitle,
    /PanelHeading\(title: "Still image", isIgnis: model\.selectedProduct == \.ignis, isVigiles: model\.selectedProduct == \.vigiles, isMedicus: model\.selectedProduct == \.medicus\)/,
    "still-image title uses PanelHeading gated on Ignis",
  );
  assert.doesNotMatch(stillTitle, /\.font\(\.headline\)/, "no headline left on still-image title");
});

test("native video title: PanelHeading with Ignis gate, no headline left", () => {
  assert.match(
    videoTitle,
    /PanelHeading\(title: "Prerecorded video", isIgnis: model\.selectedProduct == \.ignis, isVigiles: model\.selectedProduct == \.vigiles, isMedicus: model\.selectedProduct == \.medicus\)/,
    "video title uses PanelHeading gated on Ignis",
  );
  assert.doesNotMatch(videoTitle, /\.font\(\.headline\)/, "no headline left on video title");
});

test("native input-panel titles: wording unchanged", () => {
  assert.match(stillTitle, /PanelHeading\(title: "Still image"/, "still-image wording kept");
  assert.match(videoTitle, /PanelHeading\(title: "Prerecorded video"/, "video wording kept");
});
