// Musica registry entry: HN-027. Musica is registered in
// js/products.js as a studio product, NOT in the Trio PRODUCTS array
// (that array drives the camera assessment contract and is pinned by
// the web<->native parity test to the Trio three).
import test from "node:test";
import assert from "node:assert/strict";
import { PRODUCTS, PRODUCT_IDS, STUDIO_PRODUCTS, STUDIO_PRODUCT_BY_ID } from "../js/products.js";

test("musica is registered as a studio product with honest limitations", () => {
  const musica = STUDIO_PRODUCT_BY_ID.musica;
  assert.ok(musica, "musica missing from STUDIO_PRODUCTS");
  assert.equal(musica.displayName, "Meta Musica");
  assert.match(musica.limitations, /not a human performance/);
  assert.match(musica.limitations, /generated in-studio/);
  assert.match(musica.limitations, /No live model calls/);
  assert.deepEqual(musica.categories, ["chipsynth", "ambient", "boom-bap"]);
  assert.equal(STUDIO_PRODUCTS.length, 1);
});

test("Trio PRODUCTS array is untouched by the Musica registry entry", () => {
  assert.deepEqual(PRODUCT_IDS, ["vigiles", "ignis", "medicus"]);
  assert.equal(PRODUCTS.length, 3);
});
