// labs/molecules/tests/validate.test.mjs — node:test, no dependencies.
// Validates every embedded molecule JSON: atom/bond counts present,
// every bond points at real atoms with order 1-3, every element is in
// the viewer's CPK table. Run: node --test labs/molecules/tests/validate.test.mjs
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync, readdirSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const dir = join(dirname(fileURLToPath(import.meta.url)), "..", "data");
const CPK = new Set(["C", "H", "O", "N"]);
const EXPECTED = {
  "caffeine.json": { atoms: 24, bonds: 25 },
  "aspirin.json": { atoms: 21, bonds: 21 },
  "glucose.json": { atoms: 24, bonds: 24 },
  "water.json": { atoms: 3, bonds: 2 },
  "ethanol.json": { atoms: 9, bonds: 8 },
};

for (const file of Object.keys(EXPECTED)) {
  test(`${file} validates`, () => {
    const mol = JSON.parse(readFileSync(join(dir, file), "utf8"));
    assert.equal(mol.atoms.length, EXPECTED[file].atoms, "atom count");
    assert.equal(mol.bonds.length, EXPECTED[file].bonds, "bond count");
    mol.atoms.forEach((a, i) => {
      assert.ok([a.x, a.y, a.z].every(Number.isFinite), `atom ${i} coords`);
      assert.ok(a.sym && CPK.has(a.sym), `atom ${i} element in CPK table`);
    });
    mol.bonds.forEach((bd, i) => {
      assert.ok(bd.a >= 0 && bd.a < mol.atoms.length, `bond ${i} endpoint a`);
      assert.ok(bd.b >= 0 && bd.b < mol.atoms.length, `bond ${i} endpoint b`);
      assert.ok(bd.o >= 1 && bd.o <= 3, `bond ${i} order`);
    });
  });
}

test("meta.json covers the embedded set", () => {
  const meta = JSON.parse(readFileSync(join(dir, "meta.json"), "utf8"));
  const ids = new Set(meta.compounds.map((c) => c.id));
  for (const file of Object.keys(EXPECTED)) {
    assert.ok(ids.has(file.replace(".json", "")), `${file} listed`);
  }
});
