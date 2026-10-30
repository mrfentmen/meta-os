// Node built-in test runner, no dependencies:
//   node --test tests/native-settings-title-size.test.mjs
//
// IGNIS-UI-54 (Del UI push, Oct 29): native Settings panel title size
// parity. The web frontend renders every panel title as an h2 and
// styles.css gives .panel h2 15px at weight 700; the native Settings
// panel is the counterpart to the web Analysis configuration panel
// (same fields inside: endpoint, backend health, interval, scenario,
// categories), but its GroupBox("Settings") label carried no explicit
// font, so it read in the system GroupBox label style rather than the
// panel-heading treatment while the Latest title (UI-22), the timeline
// title (UI-34), and the still-image and video titles (UI-36) already
// matched their own 15px bold web rules. The fix gives the label an
// explicit 15pt bold system font, keeping its "Settings" wording. No
// Swift toolchain exists in this sandbox, so these are static checks
// on the shipped Swift.

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

const title = blockAfter('PanelHeading(title: "Settings"');

test("native Settings title: web contract — panel h2 at 15px bold", () => {
  const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
  assert.match(
    css,
    /\.panel h2 \{\s+margin: 0 0 10px;\s+font-size: 15px;\s+font-weight: 700;\s+\}/,
    "web .panel h2 is 15px weight 700",
  );
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.match(
    html,
    /<section class="panel" aria-label="Configuration">\s+<h2>Analysis configuration<\/h2>/,
    "web Configuration panel carries an h2 title",
  );
});

test("native Settings title: PanelHeading with Ignis gate, keeps its wording", () => {
  // OPS-CONSOLE-2 moved the title into the shared PanelHeading; the
  // 15pt bold itself now lives in PanelHeading's non-Ignis branch
  // (covered by native-ignis-ops-console-headings).
  assert.match(
    title,
    /PanelHeading\(title: "Settings", isIgnis: model\.selectedProduct == \.ignis\)/,
    "Settings title uses PanelHeading gated on Ignis",
  );
  assert.doesNotMatch(
    content,
    /GroupBox\("Settings"\)/,
    "no bare GroupBox(\"Settings\") label left",
  );
});

test("native Settings title: still a GroupBox label over the same panel", () => {
  assert.match(
    content,
    /GroupBox \{\s*\n\s+VStack\(alignment: \.leading, spacing: 10\)/,
    "GroupBox still wraps the Settings fields",
  );
  assert.match(
    content,
    /label: \{[\s\S]*?PanelHeading\(title: "Settings"/,
    "Settings heading is the GroupBox label",
  );
});

test("native Settings title: panel neighbors untouched", () => {
  const endpoint = blockAfter('Text("Assessment endpoint")');
  assert.match(
    endpoint,
    /\.font\(\.system\(size: 13\)\)/,
    "endpoint label keeps its UI-33 13pt size",
  );
  const categories = blockAfter(
    'Text("Categories the server may return:',
  );
  assert.match(
    categories,
    /\.font\(\.system\(size: 13\)\)/,
    "categories line keeps its UI-38 13pt size",
  );
});
