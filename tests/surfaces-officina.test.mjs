// HN-066 Officina board: workshop runs from Milo's real records.
// The real-data assertions below read the repo's actual run files —
// they prove the board renders true values, not fixtures.
// Run: node --test tests/surfaces-officina.test.mjs

import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync, readdirSync } from "node:fs";

import { officinaBoard } from "../js/surfaces.js";

const surfacesHtml = readFileSync(new URL("../surfaces.html", import.meta.url), "utf8");
const runsDir = new URL("../os/worlds/officina/runs/", import.meta.url);
const realRuns = readdirSync(runsDir)
  .filter((f) => f.endsWith(".json"))
  .map((f) => JSON.parse(readFileSync(new URL(f, runsDir), "utf8")));

test("board renders the real run files with their true grades", () => {
  const html = officinaBoard(realRuns);
  assert.match(html, /1\.062/); // forced-airflow real R_th
  assert.match(html, /1\.340/); // gap-headroom real R_th
  assert.match(html, /1\.721/); // rough-words real R_th
  assert.match(html, /proven/);
});

test("overnight run renders variants, failures with reasons, best and proven best", () => {
  const overnight = realRuns.find((r) => Number.isFinite(Number(r.n_variants)));
  assert.ok(overnight, "overnight run file present");
  const html = officinaBoard([overnight]);
  assert.match(html, /240 variants/);
  assert.match(html, /failures/);
  assert.match(html, /fin gap/);
  assert.match(html, /0\.899/);
  assert.match(html, /1\.183/);
});

test("a record with null grade renders unknown, never failed", () => {
  const html = officinaBoard([{ rough_input: "x", final_grade: null, status: null }]);
  assert.match(html, /unknown/);
  assert.doesNotMatch(html, /officina-run--failed/);
});

test("recorded failure evidence marks a run failed", () => {
  const html = officinaBoard([{
    rough_input: "bad design", rounds_used: 1,
    final_grade: { r_th_c_per_w: 9.9, feasible: false, violations: ["over temp"] },
    verification: { fresh_agrees: true }, status: "failed",
  }]);
  assert.match(html, /officina-run--failed/);
  assert.match(html, /failed/);
});

test("boards page has an officina section fetching the real run files", () => {
  assert.match(surfacesHtml, /id="board-officina"/);
  assert.match(surfacesHtml, /id="officina-content"/);
  assert.match(surfacesHtml, /os\/worlds\/officina\/runs\//);
});
