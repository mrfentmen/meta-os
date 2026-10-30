// Node built-in test runner, no dependencies:
//   node --test tests/ignis-observation-categories.test.mjs
//
// IGNIS-ONEOFONE-7 (Del's one-of-one bar, Oct 29): the Ignis
// observation-class breakdown counts the observations inside
// recorded ok Ignis assessments by the category each observation
// itself carried — the detail behind ONEOFONE-1's assessment-level
// verdict. Real state only: failures contribute nothing, other
// products move no bucket, entries with no usable observations
// array contribute nothing, observations with no usable or
// non-contract category count in the total only, and an empty or
// held session reads all zeros rather than inventing observations.
// No contract, server, or Spark-gate change.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { ignisObservationCategories } from "../js/ignis-observation-categories.js";

const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");

const obs = (category) => ({ category });
const entryWith = (observations) => ({
  status: "ok",
  product: "ignis",
  response: { observations },
});
const nestedEntryWith = (observations) => ({
  status: "ok",
  product: "ignis",
  response: { assessment: { observations } },
});

const zero = {
  total: 0,
  visibleSmoke: 0,
  visibleFlame: 0,
  steamOrFog: 0,
  flameLikeLighting: 0,
  obscuredOrDistant: 0,
  noHazard: 0,
  indeterminate: 0,
};

test("observation categories: an empty session reads all zeros", () => {
  assert.deepEqual(ignisObservationCategories([]), zero);
  assert.deepEqual(ignisObservationCategories(null), zero);
  assert.deepEqual(ignisObservationCategories(undefined), zero);
});

test("observation categories: buckets follow the observations' own categories", () => {
  const counts = ignisObservationCategories([
    entryWith([
      obs("visible smoke"),
      obs("visible smoke"),
      obs("visible flame"),
      obs("steam or fog"),
      obs("flame-like lighting"),
      obs("obscured or distant hazard"),
      obs("no hazard visible"),
      obs("indeterminate"),
      obs("not a contract category"),
      obs(null),
      obs(42),
      {},
      null,
    ]),
    nestedEntryWith([obs("visible flame")]),
    entryWith([]),
    { status: "ok", product: "ignis", response: { assessment: {} } },
    { status: "ok", product: "ignis", response: null },
    { status: "ok", product: "ignis" },
  ]);
  assert.deepEqual(counts, {
    total: 14,
    visibleSmoke: 2,
    visibleFlame: 2,
    steamOrFog: 1,
    flameLikeLighting: 1,
    obscuredOrDistant: 1,
    noHazard: 1,
    indeterminate: 1,
  });
});

test("observation categories: failed and other-product entries move no bucket", () => {
  const counts = ignisObservationCategories([
    { status: "failed", product: "ignis", response: { observations: [obs("visible smoke")] } },
    { status: "network_error", product: "ignis", response: { observations: [obs("visible smoke")] } },
    { status: "ok", product: "vigiles", response: { observations: [obs("visible smoke")] } },
    { status: "ok", product: "sanitas", response: { observations: [obs("visible smoke")] } },
    null,
    entryWith([obs("visible smoke")]),
  ]);
  assert.deepEqual(counts, {
    total: 1,
    visibleSmoke: 1,
    visibleFlame: 0,
    steamOrFog: 0,
    flameLikeLighting: 0,
    obscuredOrDistant: 0,
    noHazard: 0,
    indeterminate: 0,
  });
});

test("observation categories: panel exists in HTML, hidden except under Ignis, and wired in app.js", () => {
  assert.ok(html.includes('id="ignis-observation-categories"'));
  assert.ok(html.includes("ignis-observation-categories-panel"));
  assert.ok(css.includes(".ignis-observation-categories-panel"));
  assert.ok(css.includes('body[data-product="ignis"] .ignis-observation-categories-panel'));
  assert.ok(app.includes("ignisObservationCategories"));
  assert.ok(app.includes("els.ignisObservationCategories.textContent"));
});
