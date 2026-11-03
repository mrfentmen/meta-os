// HN-056 Lab board: no level shown higher than the record's cap.
// Run: node --test tests/surfaces-lab.test.mjs

import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

import { labBoard } from "../js/surfaces.js";

const indexHtml = readFileSync(new URL("../imperium/index.html", import.meta.url), "utf8");
const surfacesHtml = readFileSync(new URL("../surfaces.html", import.meta.url), "utf8");

test("lab board shows the cap, never the higher claimed level", () => {
  const html = labBoard([
    { id: "e1", hypothesis: "Salt water conducts", ladder_level: 9, cap: 4, status: "open" },
  ]);
  assert.match(html, /Level 4 \(capped\)/);
  assert.doesNotMatch(html, /Level 9/);
  assert.doesNotMatch(html, />9</);
});

test("lab board shows uncapped levels as recorded", () => {
  const html = labBoard([
    { id: "e2", hypothesis: "Iron rusts", ladder_level: 3, cap: 5, status: "done" },
  ]);
  assert.match(html, /Level 3/);
  assert.doesNotMatch(html, /capped/);
});

test("lab board with no records is an honest empty state, not a placeholder row", () => {
  assert.match(labBoard([]), /No lab experiments recorded yet/);
  assert.match(labBoard(null), /No lab experiments recorded yet/);
  assert.doesNotMatch(labBoard([]), /lab-row/);
});

test("lab board escapes hypothesis text", () => {
  const html = labBoard([
    { id: "e3", hypothesis: "<script>alert(1)</script>", ladder_level: 1, cap: 1, status: "open" },
  ]);
  assert.doesNotMatch(html, /<script>/);
  assert.match(html, /&lt;script&gt;/);
});

test("console links to the boards page and the page has a lab section", () => {
  assert.match(indexHtml, /href="surfaces\.html">Boards</);
  assert.match(surfacesHtml, /id="board-lab"/);
  assert.match(surfacesHtml, /id="lab-content"/);
});
