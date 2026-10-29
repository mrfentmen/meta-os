// Node built-in test runner, no dependencies:  node --test tests/contacts.test.mjs
// Covers the contacts directory store: Sanitas-first SAMPLE seed,
// per-product listing, add/remove with validation, storage persistence,
// corrupt-store fallback, and unwritable-store tolerance.

import { test } from "node:test";
import assert from "node:assert/strict";

import { ContactsStore, CONTACTS_STORAGE_KEY } from "../js/contacts.js";

function fakeStorage(initial = {}) {
  const store = new Map(Object.entries(initial));
  return {
    getItem: (key) => (store.has(key) ? store.get(key) : null),
    setItem: (key, value) => {
      store.set(key, value);
    },
    removeItem: (key) => {
      store.delete(key);
    },
    has: (key) => store.has(key),
    raw: (key) => store.get(key),
  };
}

test("contacts: first run seeds Sanitas SAMPLE contacts only", () => {
  const store = new ContactsStore({ storage: fakeStorage() });
  const sanitas = store.list("sanitas");
  assert.equal(sanitas.length, 2);
  assert.ok(sanitas.every((entry) => entry.sample === true));
  assert.ok(sanitas.every((entry) => entry.name.startsWith("SAMPLE")));
  assert.deepEqual(store.list("vigiles"), []);
  assert.deepEqual(store.list("ignis"), []);
});

test("contacts: seed persists, so a deleted sample stays deleted", () => {
  const storage = fakeStorage();
  const first = new ContactsStore({ storage });
  assert.equal(storage.has(CONTACTS_STORAGE_KEY), true);
  const [sample] = first.list("sanitas");
  assert.equal(first.remove(sample.id), true);
  const reloaded = new ContactsStore({ storage });
  assert.equal(reloaded.list("sanitas").length, 1);
});

test("contacts: add lists by product and marks real entries non-sample", () => {
  const store = new ContactsStore({ storage: fakeStorage() });
  const added = store.add({ product: "vigiles", name: "Ada Reviewer", role: "Reviewer", organization: "Review office" });
  assert.equal(added.sample, false);
  assert.equal(store.list("vigiles").length, 1);
  assert.equal(store.list("sanitas").length, 2);
  assert.equal(store.list("ignis").length, 0);
});

test("contacts: add rejects empty fields and unknown products", () => {
  const store = new ContactsStore({ storage: fakeStorage() });
  assert.throws(() => store.add({ product: "sanitas", name: "  ", role: "R", organization: "O" }), RangeError);
  assert.throws(() => store.add({ product: "sanitas", name: "N", role: "", organization: "O" }), RangeError);
  assert.throws(() => store.add({ product: "nope", name: "N", role: "R", organization: "O" }), RangeError);
});

test("contacts: remove returns false for unknown ids", () => {
  const store = new ContactsStore({ storage: fakeStorage() });
  assert.equal(store.remove(99999), false);
  assert.equal(store.count, 2);
});

test("contacts: corrupt or wrong-shaped storage loads empty but usable", () => {
  const corrupt = new ContactsStore({ storage: fakeStorage({ [CONTACTS_STORAGE_KEY]: "{not json" }) });
  assert.equal(corrupt.count, 0);
  assert.equal(corrupt.add({ product: "sanitas", name: "N", role: "R", organization: "O" }).id, 1);
  const wrongShape = new ContactsStore({ storage: fakeStorage({ [CONTACTS_STORAGE_KEY]: JSON.stringify({ id: 1 }) }) });
  assert.equal(wrongShape.count, 0);
});

test("contacts: saved contacts restore with ids intact", () => {
  const storage = fakeStorage();
  const first = new ContactsStore({ storage });
  first.add({ product: "ignis", name: "Bo", role: "R", organization: "O" });
  const reloaded = new ContactsStore({ storage });
  assert.equal(reloaded.list("ignis").length, 1);
  assert.equal(reloaded.list("ignis")[0].name, "Bo");
});

test("contacts: unwritable storage still works in memory", () => {
  const broken = {
    getItem: () => null,
    setItem: () => {
      throw new Error("denied");
    },
    removeItem: () => {
      throw new Error("denied");
    },
  };
  const store = new ContactsStore({ storage: broken });
  assert.equal(store.list("sanitas").length, 2);
  assert.equal(store.add({ product: "sanitas", name: "N", role: "R", organization: "O" }).sample, false);
});
