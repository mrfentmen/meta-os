// Node built-in test runner, no dependencies:
//   node --test tests/native-camera-guidance-size.test.mjs
//
// IGNIS-UI-29 (Del UI push, Oct 29): native camera product-guidance
// note size parity.
// HN4-5 UPDATE (2026-11-01): the Swift note tests are stripped —
// the native camera panel's guidance note was deleted with the
// WKWebView rewrite, so the Swift assertions no longer exist
// anywhere. The web contract tests below are kept verbatim.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

test("native camera guidance note: web contract — .note at 13px muted", () => {
  const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
  assert.match(
    css,
    /\.note \{\s+color: var\(--muted\);\s+font-size: 13px;/,
    "web .note is 13px muted",
  );
});

test("native camera guidance note: web note carries the note class", () => {
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.match(
    html,
    /<p id="product-guidance" class="note">/,
    "web product-guidance note carries class note",
  );
});
