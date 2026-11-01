// HN-070 Surface inventory v2: the control audit re-run across ALL
// surfaces including the new boards. Dead count must be zero — these
// checks are the mechanical enforcement of that audit.
// Run: node --test tests/surfaces-inventory.test.mjs

import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync, readdirSync, existsSync } from "node:fs";

const indexHtml = readFileSync(new URL("../index.html", import.meta.url), "utf8");
const surfacesHtml = readFileSync(new URL("../surfaces.html", import.meta.url), "utf8");
const jsDir = new URL("../js/", import.meta.url);
const jsSources = readdirSync(jsDir).filter((f) => f.endsWith(".js"))
  .map((f) => readFileSync(new URL(f, jsDir), "utf8")).join("\n");

function staticControls(html) {
  return [...html.matchAll(/<(button|input|select)\b([^>]*)>/g)];
}

test("index.html static controls unchanged from HN-020: 42 buttons, 15 inputs, 2 selects", () => {
  const tags = staticControls(indexHtml).map((m) => m[1]);
  assert.equal(tags.filter((t) => t === "button").length, 42);
  assert.equal(tags.filter((t) => t === "input").length, 15);
  assert.equal(tags.filter((t) => t === "select").length, 2);
});

test("every id'd index.html control has a listener or read site in js/", () => {
  const ids = staticControls(indexHtml)
    .map((m) => (m[2].match(/id="([^"]+)"/) || [])[1])
    .filter(Boolean);
  assert.ok(ids.length > 40);
  for (const id of ids) {
    assert.ok(jsSources.includes(id), `no wiring for ${id}`);
  }
});

test("id-less index.html controls work by group listener or native behavior", () => {
  assert.match(jsSources, /querySelectorAll\("\[data-cmd-product\]"/);
  assert.match(jsSources, /querySelectorAll\("\[data-cmd-mode\]"/);
  assert.match(jsSources, /querySelectorAll\("\.logo-swatch\[data-logo-color\]"/);
  const radios = [...indexHtml.matchAll(/<input type="radio" name="product"/g)];
  assert.equal(radios.length, 3);
  assert.equal((indexHtml.match(/<details/g) || []).length, 27);
});

test("index.html links resolve", () => {
  assert.ok(existsSync(new URL("../design/meta-ascii-logo-studio.html", import.meta.url)));
  assert.ok(existsSync(new URL("../surfaces.html", import.meta.url)));
});

test("boards page has zero interactive controls, so zero dead controls", () => {
  assert.equal(staticControls(surfacesHtml).length, 0);
  assert.equal((surfacesHtml.match(/<details/g) || []).length, 0);
});

test("every boards nav link resolves to a section on the page", () => {
  const ids = new Set([...surfacesHtml.matchAll(/id="([^"]+)"/g)].map((m) => m[1]));
  const internal = [...surfacesHtml.matchAll(/<a\b[^>]*href="(#[^"]+)"/g)].map((m) => m[1]);
  assert.equal(internal.length, 13);
  for (const href of internal) {
    assert.ok(ids.has(href.slice(1)), `unresolved ${href}`);
  }
  assert.match(surfacesHtml, /href="index\.html"/);
});

test("every boards content region is written by the page script", () => {
  const regions = [...surfacesHtml.matchAll(/id="([a-z-]+content)"/g)].map((m) => m[1]);
  assert.equal(regions.length, 11);
  for (const id of regions) {
    assert.ok(surfacesHtml.includes(`getElementById("${id}")`), `unwritten region ${id}`);
  }
});
