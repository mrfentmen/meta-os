// HN-070 Surface inventory v2: the control audit re-run across ALL
// surfaces including the new boards. Dead count must be zero — these
// checks are the mechanical enforcement of that audit.
// Run: node --test tests/surfaces-inventory.test.mjs

import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync, readdirSync, existsSync } from "node:fs";

const indexHtml = readFileSync(new URL("../imperium/index.html", import.meta.url), "utf8");
const surfacesHtml = readFileSync(new URL("../surfaces.html", import.meta.url), "utf8");
const jsDir = new URL("../js/", import.meta.url);
const jsSources = readdirSync(jsDir).filter((f) => f.endsWith(".js"))
  .map((f) => readFileSync(new URL(f, jsDir), "utf8")).join("\n");

function staticControls(html) {
  return [...html.matchAll(/<(button|input|select)\b([^>]*)>/g)];
}

test("index.html static controls: 35 buttons, 14 inputs, 2 selects (LOGO-1 color controls removed 2026-11-01)", () => {
  const tags = staticControls(indexHtml).map((m) => m[1]);
  assert.equal(tags.filter((t) => t === "button").length, 35);
  assert.equal(tags.filter((t) => t === "input").length, 14);
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
  const radios = [...indexHtml.matchAll(/<input type="radio" name="product"/g)];
  assert.equal(radios.length, 3);
  assert.equal((indexHtml.match(/<details/g) || []).length, 27);
});

test("boards page is reachable and the hub page it replaced is gone", () => {
  assert.ok(existsSync(new URL("../surfaces.html", import.meta.url)));
  // The root index.html was the app hub and the boards page used to link back
  // to it. Both are retired (2026-11-04): the dock lists the apps, and this
  // page is the site root. A link to it would be a dead link.
  assert.equal(existsSync(new URL("../index.html", import.meta.url)), false);
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
  // The page's only outward links are the three divisions. Every one of them
  // must exist on disk — a nav chip that 404s is the same dead surface the
  // audit is here to catch.
  const outward = [...surfacesHtml.matchAll(/<a\b[^>]*href="(?!http|\.\.\/)([^"#][^"]*)"/g)]
    .map((m) => m[1])
    .filter((href) => !href.startsWith("#"));
  assert.deepEqual(outward.sort(), ["trio/ignis.html", "trio/medicus.html", "trio/vigiles.html"]);
  for (const href of outward) {
    assert.ok(existsSync(new URL("../" + href, import.meta.url)), `missing ${href}`);
  }
});

test("every boards content region is written by the page script", () => {
  const regions = [...surfacesHtml.matchAll(/id="([a-z-]+content)"/g)].map((m) => m[1]);
  assert.equal(regions.length, 11);
  for (const id of regions) {
    assert.ok(surfacesHtml.includes(`getElementById("${id}")`), `unwritten region ${id}`);
  }
});
