// Node built-in test runner, no dependencies:
//   node --test tests/native-settings-categories-size.test.mjs
//
// IGNIS-UI-38 (Del UI push, Oct 29): native Settings categories line
// size parity. The web Settings notes carry class .note at 13px muted
// — but the native Settings panel's "Categories the server may
// return" line used .caption (12pt), so it read one point smaller
// than the web panel's Settings notes while the backend-health and
// sampling-disclosure lines (UI-32) and the endpoint and scenario
// labels (UI-33) already matched their own 13px web rules. The fix
// gives the line a 13pt system font, keeping its muted color, its
// wrapping, and its wording. No Swift toolchain exists in this
// sandbox, so these are static checks on the shipped Swift.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const content = readFileSync(
  new URL("../native/Sources/MetaTrio/Views/ContentView.swift", import.meta.url),
  "utf8",
);

function blockAfter(marker, length = 400) {
  const start = content.indexOf(marker);
  assert.ok(start >= 0, `${marker} exists`);
  return content.slice(start, start + length);
}

const categories = blockAfter("Categories the server may return:");

test("native Settings categories line: web contract — .note at 13px muted", () => {
  const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
  assert.match(
    css,
    /\.note \{\s+color: var\(--muted\);\s+font-size: 13px;/,
    "web .note is 13px muted",
  );
});

test("native Settings categories line: takes 13pt, keeps muted color", () => {
  assert.match(
    categories,
    /\.font\(\.system\(size: 13\)\)/,
    "categories line takes 13pt",
  );
  assert.doesNotMatch(categories, /\.font\(\.caption\)/, "no caption left on categories line");
  assert.match(
    categories,
    /\.foregroundStyle\(\.secondary\)/,
    "categories line keeps muted color",
  );
});

test("native Settings categories line: keeps wrapping", () => {
  assert.match(
    categories,
    /\.fixedSize\(horizontal: false, vertical: true\)/,
    "categories line keeps wrapping",
  );
});

test("native Settings categories line: wording unchanged", () => {
  assert.match(
    categories,
    /Categories the server may return: \\\(model\.config\.categories\.joined\(separator: ", "\)\)\./,
    "categories line wording unchanged",
  );
});
