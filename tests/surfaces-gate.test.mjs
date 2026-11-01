// HN-058 Gate status page: true state driven by gate directory files.
// Run: node --test tests/surfaces-gate.test.mjs

import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

import { gateState, gateStatusPage } from "../js/surfaces.js";

const surfacesHtml = readFileSync(new URL("../surfaces.html", import.meta.url), "utf8");

test("gate state follows file precedence: earned > running > prepared > not prepared", () => {
  assert.equal(gateState(["earned.json", "running.json", "delaney-set.json"]), "earned");
  assert.equal(gateState(["running.json", "delaney-set.json"]), "running");
  assert.equal(gateState(["delaney-set.json"]), "prepared");
  assert.equal(gateState([]), "not prepared");
  assert.equal(gateState(null), "not prepared");
});

test("gate page shows the true state and the files behind it", () => {
  const html = gateStatusPage({ files: ["delaney-set.json"] });
  assert.match(html, /data-gate-state="prepared"/);
  assert.match(html, /delaney-set\.json/);
  const empty = gateStatusPage(null);
  assert.match(empty, /data-gate-state="not prepared"/);
  assert.match(empty, /No gate files in this repo yet/);
});

test("boards page has a gate section wired to the manifest", () => {
  assert.match(surfacesHtml, /id="board-gate"/);
  assert.match(surfacesHtml, /id="gate-content"/);
  assert.match(surfacesHtml, /gates\/delaney\/manifest\.json/);
});
