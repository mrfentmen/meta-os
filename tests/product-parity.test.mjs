// Node built-in test runner, no dependencies:
//   node --test tests/product-parity.test.mjs
//
// Web <-> native product-config parity. The web frontend (js/products.js)
// and the native macOS app (native/Sources/MetaTrio/Models/ProductConfig.swift)
// must show the same product identity: same display name, department,
// tagline, categories, evaluation scenarios, limitations, and input
// guidance for each product, in the same order. A drift here means the two
// frontends describe the same product differently to the user, so this
// test reads the Swift source (it cannot run Swift in this sandbox) and
// asserts deep equality against the web config. The native accent is a
// SwiftUI color name; the web accent is a hex value, so the mapping is
// asserted separately rather than compared as raw strings.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

import { PRODUCTS, PRODUCT_IDS } from "../js/products.js";

const ACCENT_HEX_BY_COLOR_NAME = {
  blue: "#4f7ec2",
  red: "#d92b2b",
  green: "#5da864",
};

function stringField(block, name) {
  const match = block.match(new RegExp(`${name}: "([^"]*)"`));
  assert.ok(match, `native config is missing ${name}`);
  return match[1];
}

function listField(block, name) {
  const match = block.match(new RegExp(`${name}: \\[([\\s\\S]*?)\\n        \\]`));
  assert.ok(match, `native config is missing ${name}`);
  return [...match[1].matchAll(/"([^"]*)"/g)].map((m) => m[1]);
}

function parseNativeConfigs() {
  const swift = readFileSync(
    new URL("../native/Sources/MetaTrio/Models/ProductConfig.swift", import.meta.url),
    "utf8",
  );
  const configs = {};
  for (const id of ["vigiles", "ignis", "medicus"]) {
    const start = swift.indexOf(`static let ${id} = ProductConfig(`);
    assert.notEqual(start, -1, `native config is missing ${id}`);
    const end = swift.indexOf("\n    )", start);
    assert.notEqual(end, -1, `native config for ${id} has no closing paren`);
    const block = swift.slice(start, end);
    configs[id] = {
      displayName: stringField(block, "displayName"),
      department: stringField(block, "department"),
      tagline: stringField(block, "tagline"),
      accentColorName: stringField(block, "accentColorName"),
      categories: listField(block, "categories"),
      scenarios: listField(block, "scenarios"),
      limitations: stringField(block, "limitations"),
      inputGuidance: stringField(block, "inputGuidance"),
    };
  }
  return configs;
}

const native = parseNativeConfigs();

test("web and native list the same products in the same order", () => {
  assert.deepEqual(PRODUCT_IDS, ["vigiles", "ignis", "medicus"]);
  assert.deepEqual(Object.keys(native), PRODUCT_IDS);
});

for (const product of PRODUCTS) {
  test(`web and native agree on every ${product.id} config string`, () => {
    const n = native[product.id];
    assert.equal(n.displayName, product.displayName);
    assert.equal(n.department, product.department);
    assert.equal(n.tagline, product.tagline);
    assert.deepEqual(n.categories, product.categories);
    assert.deepEqual(n.scenarios, product.scenarios);
    assert.equal(n.limitations, product.limitations);
    assert.equal(n.inputGuidance, product.inputGuidance);
  });
}

test("web accent hex matches the native accent color name", () => {
  for (const product of PRODUCTS) {
    const colorName = native[product.id].accentColorName;
    assert.ok(
      colorName in ACCENT_HEX_BY_COLOR_NAME,
      `unknown native accent color ${colorName}`,
    );
    assert.equal(product.accent, ACCENT_HEX_BY_COLOR_NAME[colorName]);
  }
});
