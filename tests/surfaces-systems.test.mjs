// HN-068 Systems home: status chips from each world's own pack.json.
// The real-data assertions read the repo's actual pack files.
// Run: node --test tests/surfaces-systems.test.mjs

import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

import { systemsChip, systemsHome } from "../js/surfaces.js";

const surfacesHtml = readFileSync(new URL("../surfaces.html", import.meta.url), "utf8");
const worldDirs = ["custos", "dep", "doe", "dsny", "ems", "fdny", "hospital", "mta", "nypd", "officina"];
const realPacks = worldDirs.map((dir) => ({
  dir,
  pack: JSON.parse(readFileSync(new URL(`../os/worlds/${dir}/pack.json`, import.meta.url), "utf8")),
}));

test("chips match the real pack statuses: partial stays partial, spec stays spec", () => {
  for (const { dir, pack } of realPacks) {
    assert.equal(systemsChip(pack.status), pack.status, dir);
  }
  assert.equal(systemsChip("partial"), "partial");
  assert.equal(systemsChip("spec"), "spec");
});

test("unknown or missing status is never upgraded to live", () => {
  assert.equal(systemsChip(undefined), "not built");
  assert.equal(systemsChip("built"), "not built");
  assert.equal(systemsChip(""), "not built");
});

test("home renders real packs with their true chips", () => {
  const html = systemsHome(realPacks.map(({ pack }) => ({ name: pack.pack_name, status: pack.status })));
  assert.match(html, /systems-chip--partial/);
  assert.match(html, /systems-chip--spec/);
  assert.match(html, /Meta Custos machine watch world pack/);
  assert.doesNotMatch(html, /systems-chip--live/);
});

test("boards page has a systems section fetching the real world packs", () => {
  assert.match(surfacesHtml, /id="board-systems"/);
  assert.match(surfacesHtml, /id="systems-content"/);
  assert.match(surfacesHtml, /os\/worlds\/\$\{dir\}\/pack\.json/);
});
