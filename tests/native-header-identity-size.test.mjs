// Node built-in test runner, no dependencies:
//   node --test tests/native-header-identity-size.test.mjs
//
// IGNIS-UI-41 (Del UI push, Oct 29): native header identity row
// department and tagline size parity.
// HN4-5 UPDATE (2026-11-01): the Swift department/tagline tests
// are stripped — the native HeaderView row was deleted with the
// WKWebView rewrite, so the Swift assertions no longer exist
// anywhere. The web contract tests below are kept verbatim.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

test("native header department: web contract — .product-department at 13px", () => {
  const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
  assert.match(
    css,
    /\.product-department \{\s+margin: 0 0 2px;\s+font-size: 13px;/,
    "web .product-department is 13px",
  );
});

test("native header tagline: web contract — .product-tagline at 14px", () => {
  const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
  assert.match(
    css,
    /\.product-tagline \{\s+margin: 0;\s+font-size: 14px;/,
    "web .product-tagline is 14px",
  );
});
