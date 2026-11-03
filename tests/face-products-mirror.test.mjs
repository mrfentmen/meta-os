// CB2-420 — the product categories in js/products.js and their real mirror.
//
// The mirror is not a copy written for this test: `js/products.js` says it is
// mirrored from native/Sources/MetaTrio/Models/ProductConfig.swift, so the test
// reads the Swift file the pipeline actually ships. Two lists that disagree mean
// the browser and the app offer different categories for the same product.
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import url from "node:url";
import { CATEGORY_DEFINITIONS, PRODUCTS, STUDIO_PRODUCTS, definitionFor } from "../js/products.js";

const ROOT = path.resolve(path.dirname(url.fileURLToPath(import.meta.url)), "..");
const swift = fs.readFileSync(
  path.join(ROOT, "native", "Sources", "MetaTrio", "Models", "ProductConfig.swift"),
  "utf8",
);

// `static let <name> = ProductConfig(` ... `categories: [ ... ],`
function swiftCategories() {
  const out = {};
  const blocks = [...swift.matchAll(/static let (\w+) = ProductConfig\(([\s\S]*?)\n {4}\)/g)];
  for (const [, name, body] of blocks) {
    const id = body.match(/product: \.(\w+)/);
    const cats = body.match(/categories: \[([\s\S]*?)\],\s*\n\s*scenarios:/);
    if (!id || !cats) continue;
    const ids = [...cats[1].matchAll(/"([^"]+)"/g)].map((m) => m[1]);
    const productId = id[1] === "scienceLab" ? "science-lab" : id[1];
    out[productId] = ids;
  }
  return out;
}

test("CB2-420 every product's categories agree between products.js and ProductConfig.swift", () => {
  const mirrored = swiftCategories();
  assert.ok(Object.keys(mirrored).length >= 4, "read the Swift configs: " + Object.keys(mirrored).join(", "));

  for (const product of PRODUCTS) {
    const theirs = mirrored[product.id];
    assert.ok(theirs, product.id + " exists in the Swift mirror");
    assert.deepEqual(
      product.categories,
      theirs,
      product.id + " categories match the mirror in order",
    );
    assert.ok(product.categories.every((c) => typeof c === "string" && c.trim() !== ""), product.id + " has no blank category");
  }

  // No product in the mirror is missing from the browser data.
  const ours = new Set(PRODUCTS.map((p) => p.id));
  for (const id of Object.keys(mirrored)) assert.ok(ours.has(id), id + " is in products.js too");
});

test("CB2-421 every category carries its own non-empty definition", () => {
  const all = [...PRODUCTS, ...STUDIO_PRODUCTS];
  assert.ok(all.length >= 5, "read the product and studio tables");

  for (const product of all) {
    for (const category of product.categories) {
      const text = definitionFor(category);
      assert.equal(typeof text, "string", product.id + "/" + category);
      assert.ok(text.trim().length > 10, "definition is a sentence, not a label: " + category);
      assert.ok(!text.toLowerCase().startsWith(category.toLowerCase() + " is"), "a definition does not repeat its own name");
    }
  }

  // A category nobody defined is refused by name, never rendered blank.
  assert.throws(() => definitionFor("birds in the sky"), /no definition for category/);
  assert.throws(() => definitionFor(undefined), /no definition for category/);

  // The crowd-gathered entry keeps its narrow definition: a stationary crowd,
  // not any people near each other.
  const crowd = CATEGORY_DEFINITIONS["crowd gathered"];
  assert.match(crowd, /stationary/i);
  assert.match(crowd, /assembled/i);
  assert.match(crowd, /normal activity/i, "and it points at the category it is not");
});
