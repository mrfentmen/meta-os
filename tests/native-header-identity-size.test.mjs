// Node built-in test runner, no dependencies:
//   node --test tests/native-header-identity-size.test.mjs
//
// IGNIS-UI-41 (Del UI push, Oct 29): native header identity row
// department and tagline size parity. The web identity row carries
// its department as .product-department at 13px and its tagline as
// .product-tagline at 14px — but the native HeaderView row used
// .subheadline (15pt) for both, so the department read two points
// larger and the tagline one point larger than the web row while
// the Product label (UI-40) already matched its own 13px web rule.
// The fix gives the department a 13pt system font and the tagline
// a 14pt system font, keeping the department's semibold weight and
// the tagline's muted color. No Swift toolchain exists in this
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

const department = blockAfter("Text(model.config.department)");
const tagline = blockAfter("Text(model.config.tagline)");

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

test("native header department: takes 13pt, keeps semibold weight", () => {
  assert.match(
    department,
    /\.font\(\.system\(size: 13\)\)/,
    "department takes 13pt",
  );
  assert.doesNotMatch(department, /\.font\(\.subheadline\)/, "no subheadline left on department");
  assert.match(
    department,
    /\.fontWeight\(\.semibold\)/,
    "department keeps semibold weight",
  );
});

test("native header tagline: takes 14pt, keeps muted color", () => {
  assert.match(
    tagline,
    /\.font\(\.system\(size: 14\)\)/,
    "tagline takes 14pt",
  );
  assert.doesNotMatch(tagline, /\.font\(\.subheadline\)/, "no subheadline left on tagline");
  assert.match(
    tagline,
    /\.foregroundStyle\(\.secondary\)/,
    "tagline keeps muted color",
  );
});
