// Node built-in test runner, no dependencies:
//   node --test tests/surfaces-region-boxes.test.mjs
//
// BUILD WAVE W1 follow-up (2026-11-02): region boxes on the landed
// contract. Regions are 0-1000 relative frame coordinates {x, y, w, h}
// (integers, w/h >= 1), null when scene-wide — the shape js/schema.js
// validates and server/queue/spark_gen.py prompts for. The renderer
// draws only what the assessment carries — never an invented box.

import { test } from "node:test";
import assert from "node:assert/strict";

import { regionBoxes } from "../js/surfaces.js";
import { PRODUCT_PROFILES, buildSparkPrompt } from "../server/model.mjs";

function assessment(observations) {
  return { product: "vigiles", observations };
}

function obs(category, region) {
  return { category, description: "seen", evidence: "frame", confidence: 0.9, region };
}

test("a valid region draws one outline with percent position and category label", () => {
  const html = regionBoxes(assessment([obs("crowd gathered", { x: 100, y: 200, w: 300, h: 400 })]));
  assert.match(html, /class="region-boxes"/);
  assert.match(html, /class="region-box"/);
  assert.match(html, /left:10%;top:20%;width:30%;height:40%/);
  assert.match(html, />crowd gathered</);
});

test("a null region (scene-wide) draws nothing", () => {
  assert.equal(regionBoxes(assessment([obs("normal activity", null)])), "");
});

test("a missing region draws nothing", () => {
  const { region, ...noRegion } = obs("normal activity", { x: 0, y: 0, w: 10, h: 10 });
  void region;
  assert.equal(regionBoxes(assessment([noRegion])), "");
});

test("malformed regions are skipped, never drawn", () => {
  const bad = [
    { x: 0, y: 0, w: 0, h: 10 },
    { x: -1, y: 0, w: 10, h: 10 },
    { x: 0, y: 0, w: 10 },
    { x: 0.5, y: 0, w: 10, h: 10 },
    { x: 0, y: 0, width: 10, height: 10 },
    "left third",
    [100, 200, 300, 400],
  ];
  for (const region of bad) {
    assert.equal(regionBoxes(assessment([obs("visible smoke", region)])), "", JSON.stringify(region));
  }
});

test("mixed observations: only the drawable regions draw, in order", () => {
  const html = regionBoxes(assessment([
    obs("normal activity", null),
    obs("crowd gathered", { x: 0, y: 0, w: 1000, h: 1000 }),
    obs("possible altercation", { x: 500, y: 500, w: 250, h: 250 }),
  ]));
  assert.equal((html.match(/class="region-box"/g) || []).length, 2);
  assert.match(html, /left:0%;top:0%;width:100%;height:100%/);
  assert.match(html, /left:50%;top:50%;width:25%;height:25%/);
});

test("category labels are escaped", () => {
  const html = regionBoxes(assessment([
    obs("<script>alert(1)</script>", { x: 0, y: 0, w: 10, h: 10 }),
  ]));
  assert.doesNotMatch(html, /<script>/);
  assert.match(html, /&lt;script&gt;/);
});

test("no observations, or no assessment, draws nothing", () => {
  assert.equal(regionBoxes(assessment([])), "");
  assert.equal(regionBoxes(null), "");
  assert.equal(regionBoxes({}), "");
});

test("model.mjs shape line mirrors spark_gen.py: region {x, y, w, h} or null", () => {
  const prompt = buildSparkPrompt(PRODUCT_PROFILES.vigiles, { product: "vigiles", timestamp: "2026-11-02T06:00:00Z" });
  assert.match(prompt, /"region": \{"x": <0\.\.1000>, "y": <0\.\.1000>, "w": <0\.\.1000>, "h": <0\.\.1000>\} or null/);
});
