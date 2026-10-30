// Node built-in test runner, no dependencies:
//   node --test tests/ignis-uncertainty-disclosure.test.mjs
//
// IGNIS-ONEOFONE-5 (Del's one-of-one bar, Oct 29): the Ignis
// uncertainty-disclosure panel counts recorded Ignis assessments by
// the uncertainty items they themselves disclosed — disclosed, none
// disclosed, or unrecorded when no usable uncertainty array exists.
// Real state only: failures contribute nothing, other products move
// no bucket, and an empty or held session reads all zeros rather
// than inventing candor. A disclosed-nothing assessment is never
// claimed reliable. No contract, server, or Spark-gate change.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { ignisUncertaintyDisclosure } from "../js/ignis-uncertainty.js";

const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");

const ok = (product, response) => ({
  status: "ok",
  product,
  response,
});
const withUncertainty = (uncertainty) => ({
  assessment: { uncertainty },
});

const zero = {
  total: 0,
  disclosed: 0,
  noneDisclosed: 0,
  unrecorded: 0,
};

test("uncertainty disclosure: an empty session reads all zeros", () => {
  assert.deepEqual(ignisUncertaintyDisclosure([]), zero);
  assert.deepEqual(ignisUncertaintyDisclosure(null), zero);
  assert.deepEqual(ignisUncertaintyDisclosure(undefined), zero);
});

test("uncertainty disclosure: buckets follow the recorded uncertainty arrays", () => {
  const counts = ignisUncertaintyDisclosure([
    ok("ignis", withUncertainty(["distant view", "low light"])),
    ok("ignis", withUncertainty(["single frame"])),
    ok("ignis", withUncertainty([])),
    ok("ignis", withUncertainty("not an array")),
    ok("ignis", withUncertainty(null)),
    ok("ignis", { assessment: {} }),
    ok("ignis", {}),
    ok("ignis", null),
    { status: "ok", product: "ignis" },
  ]);
  assert.deepEqual(counts, {
    total: 9,
    disclosed: 2,
    noneDisclosed: 1,
    unrecorded: 6,
  });
});

test("uncertainty disclosure: failures and other products move no bucket", () => {
  const counts = ignisUncertaintyDisclosure([
    { status: "failed", product: "ignis", response: withUncertainty(["x"]) },
    { status: "network_error", product: "ignis", response: withUncertainty(["x"]) },
    ok("vigiles", withUncertainty(["x"])),
    ok("sanitas", withUncertainty(["x"])),
    ok("ignis", withUncertainty(["x"])),
  ]);
  assert.deepEqual(counts, {
    total: 1,
    disclosed: 1,
    noneDisclosed: 0,
    unrecorded: 0,
  });
});

test("uncertainty disclosure: panel exists in HTML, hidden except under Ignis, and wired in app.js", () => {
  assert.ok(html.includes('id="ignis-uncertainty"'));
  assert.ok(html.includes("ignis-uncertainty-panel"));
  assert.ok(css.includes(".ignis-uncertainty-panel"));
  assert.ok(css.includes('body[data-product="ignis"] .ignis-uncertainty-panel'));
  assert.ok(app.includes("ignisUncertaintyDisclosure"));
  assert.ok(app.includes("els.ignisUncertainty.textContent"));
});
