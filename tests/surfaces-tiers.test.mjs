// HN-060 Tier colours audit: rendering matches the display table
// (FLAG_TIERS in js/command-loop.js) for all categories, all three
// divisions. One real fix found by this audit: untiered incident rows
// used to inherit the red incident color; they now render neutral,
// and red-tier rows carry an explicit red class.
// Screenshot proof is OWED at Mac gate (no browser in this sandbox):
// see docs/TIER_SCREENSHOT_PACK.md. No screenshot is claimed here.
// Run: node --test tests/surfaces-tiers.test.mjs

import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

import { flagTier, loopItemTierClass, FLAG_TIERS } from "../js/command-loop.js";

const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
const mapJs = readFileSync(new URL("../js/command-map.js", import.meta.url), "utf8");
const surfacesHtml = readFileSync(new URL("../surfaces.html", import.meta.url), "utf8");

function cssColor(rule) {
  // Parse declarations, not a substring: "border-color" must never
  // satisfy a lookup for "color".
  const block = css.match(new RegExp(`\\.${rule}\\s*\\{([^}]*)\\}`));
  if (!block) return null;
  for (const decl of block[1].split(";")) {
    const idx = decl.indexOf(":");
    if (idx === -1) continue;
    if (decl.slice(0, idx).trim() === "color") return decl.slice(idx + 1).trim();
  }
  return null;
}

test("every display-table category in all three divisions maps to its table tier", () => {
  const divisions = ["vigiles", "ignis", "medicus"];
  let checked = 0;
  for (const div of divisions) {
    for (const cat of FLAG_TIERS[div].yellow) {
      assert.equal(flagTier(div, cat), "yellow", `${div}/${cat}`);
      checked += 1;
    }
    for (const cat of FLAG_TIERS[div].red) {
      assert.equal(flagTier(div, cat), "red", `${div}/${cat}`);
      checked += 1;
    }
  }
  assert.equal(checked, 31);
});

test("tier class mapping: yellow and red each get a class, untiered gets none", () => {
  assert.equal(loopItemTierClass("yellow"), " cmd-loop-item--incident-yellow");
  assert.equal(loopItemTierClass("red"), " cmd-loop-item--incident-red");
  assert.equal(loopItemTierClass(null), "");
  assert.equal(loopItemTierClass(undefined), "");
});

test("CSS colors match the table: yellow #ffe27a, red #ffb3ab, incident base not red", () => {
  assert.equal(cssColor("cmd-loop-item--incident-yellow"), "#ffe27a");
  assert.equal(cssColor("cmd-loop-item--incident-red"), "#ffb3ab");
  assert.equal(cssColor("cmd-ribbon--yellow"), "#ffe27a");
  assert.equal(cssColor("cmd-ribbon--red"), "#ffb3ab");
  assert.notEqual(cssColor("cmd-loop-item--incident"), "#ffb3ab");
});

test("loop feed uses the tier class helper and the ribbon uses both tier classes", () => {
  assert.match(mapJs, /loopItemTierClass\(item\.tier\)/);
  assert.match(mapJs, /cmd-ribbon--\$\{tier\}/);
});

test("boards page carries the tier audit section with true counts", () => {
  assert.match(surfacesHtml, /id="board-tiers"/);
  assert.match(surfacesHtml, /31 categories/);
  assert.match(surfacesHtml, /screenshots owed at Mac gate/);
});
