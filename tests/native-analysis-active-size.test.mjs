// Node built-in test runner, no dependencies:
//   node --test tests/native-analysis-active-size.test.mjs
//
// IGNIS-UI-45 (Del UI push, Oct 29): native ANALYSIS ACTIVE size parity.
// HN4-5 UPDATE (2026-11-01): the Swift banner tests are stripped —
// the native camera panel's ANALYSIS ACTIVE banner was deleted with
// the WKWebView rewrite, so the Swift assertions no longer exist
// anywhere. The web contract below is kept verbatim: the web line
// is #analysis-active with class .note (13px).

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

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
