// Node built-in test runner, no dependencies:
//   node --test tests/native-header-flame-chip-size.test.mjs
//
// IGNIS-UI-42 (Del UI push, Oct 29): native header flame chip type
// parity.
// HN4-5 UPDATE (2026-11-01): the Swift chip tests are stripped —
// the native header's Ignis-only flame chip was deleted with the
// WKWebView rewrite, so the Swift assertions no longer exist
// anywhere. The web contract test below is kept verbatim.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

test("native flame chip: web contract — .product-badge at 13px, 700, 0.04em tracking", () => {
  const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
  assert.match(
    css,
    /\.product-badge \{\s+margin: 0;\s+font-size: 13px;\s+font-weight: 700;\s+letter-spacing: 0\.04em;/,
    "web .product-badge is 13px, weight 700, letter-spacing 0.04em",
  );
});
