// Node built-in test runner, no dependencies:
//   node --test tests/native-header-product-label-size.test.mjs
//
// IGNIS-UI-40 (Del UI push, Oct 29): native header Product label size
// parity. The web frontend carries its field labels as <label>
// elements — styles.css sets label at 13px in --muted — but the native
// header's "Product" label above the segmented product picker used
// .caption (12pt), so it read one point smaller than the web labels
// while the endpoint and scenario labels (UI-33) already matched
// their own 13px web rule. The fix gives the label a 13pt system
// font, keeping its muted color and its wording. No Swift toolchain
// exists in this sandbox, so these are static checks on the shipped
// Swift.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const content = readFileSync(
  new URL("../native/Sources/MetaTrio/Views/ContentView.swift", import.meta.url),
  "utf8",
);

function blockAfter(marker, length = 800) {
  const start = content.indexOf(marker);
  assert.ok(start >= 0, `${marker} exists`);
  return content.slice(start, start + length);
}

const productLabel = blockAfter('Text("Product")');

test("native header Product label: web contract — label at 13px muted", () => {
  const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
  assert.match(
    css,
    /label \{\s+display: block;\s+margin: 10px 0 4px;\s+font-size: 13px;\s+color: var\(--muted\);/,
    "web label is 13px muted",
  );
});

test("native header Product label: it is the picker's visible label", () => {
  assert.match(
    content,
    /Picker\("Product", selection: \$model\.selectedProduct\)/,
    "picker carries the Product label",
  );
  assert.match(productLabel, /\.labelsHidden\(\)/, "picker hides its own label");
});

test("native header Product label: takes 13pt, keeps muted color", () => {
  assert.match(
    productLabel,
    /\.font\(\.system\(size: 13\)\)/,
    "Product label takes 13pt",
  );
  assert.doesNotMatch(productLabel, /\.font\(\.caption\)/, "no caption left on Product label");
  assert.match(
    productLabel,
    /\.foregroundStyle\(\.secondary\)/,
    "Product label keeps muted color",
  );
});

test("native header Product label: wording and picker unchanged", () => {
  assert.match(productLabel, /Text\("Product"\)/, "label wording unchanged");
  assert.match(
    productLabel,
    /\.pickerStyle\(\.segmented\)/,
    "picker keeps segmented style",
  );
  assert.match(
    productLabel,
    /\.accessibilityLabel\("Product"\)/,
    "picker keeps Product accessibility label",
  );
});
