// HN-069 Print stylesheet: printing the boards page prints only the
// incident record (evidence + BOLO + timeline + receipt).
// Run: node --test tests/surfaces-print.test.mjs

import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const surfacesHtml = readFileSync(new URL("../surfaces.html", import.meta.url), "utf8");
const stylesCss = readFileSync(new URL("../styles.css", import.meta.url), "utf8");

test("exactly the four incident sections carry the incident-record class", () => {
  const marked = [...surfacesHtml.matchAll(/<section class="board-section incident-record" id="([^"]+)"/g)]
    .map((m) => m[1]);
  assert.deepEqual(marked.sort(), ["board-bolo", "board-evidence", "board-receipt", "board-timeline"]);
});

test("print block hides nav, controls, and non-incident boards, prints the record black on white", () => {
  const printBlock = stylesCss.slice(stylesCss.indexOf("@media print"));
  assert.ok(printBlock.length > 0, "print block present");
  assert.match(printBlock, /\.boards-nav/);
  assert.match(printBlock, /button/);
  assert.match(printBlock, /\.board-section:not\(\.incident-record\)/);
  assert.match(printBlock, /\.incident-record/);
  assert.match(printBlock, /color: #000/);
  assert.match(printBlock, /background: #fff/);
});
