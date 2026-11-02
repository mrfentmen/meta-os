// Node built-in test runner, no dependencies:
//   node --test tests/native-footer-size.test.mjs
//
// IGNIS-UI-23 (Del UI push, Oct 29): native footer disclaimer size
// parity.
// HN4-5 UPDATE (2026-11-01): the Swift disclaimer tests are
// stripped — the native window's footer disclaimer was deleted
// with the WKWebView rewrite, so the Swift assertions no longer
// exist anywhere. The web contract tests below are kept verbatim.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const disclaimer =
  "Experimental prototype for staged, consenting scenarios. Not an operational law-enforcement, fire-detection, or enforcement system. This app never contacts police or emergency services, performs no face recognition or identity inference, and never dispatches or cites automatically.";

test("native footer: web contract — .footer at 13px muted", () => {
  const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
  assert.match(
    css,
    /\.footer \{\s+padding: 12px 16px 20px;\s+max-width: 1240px;\s+margin: 0 auto;\s+color: var\(--muted\);\s+font-size: 13px;/,
    "web .footer is 13px muted",
  );
});

test("native footer: web footer carries the same disclaimer words", () => {
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.ok(
    html.includes(`<footer class="footer">`) &&
      html.includes(`<p>${disclaimer}</p>`),
    "web footer carries the disclaimer verbatim",
  );
});
