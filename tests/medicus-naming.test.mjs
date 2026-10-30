// Node built-in test runner, no dependencies:
//   node --test tests/medicus-naming.test.mjs
//
// HANA Agent1: MEDICUS-NAMING — the Trio pivot (Oct 29, Pax OFFICIAL)
// replaced Sanitas with Medicus, but four Agent 1 spots still said
// Sanitas: two comments in js/app.js, two comments in styles.css,
// and two Ignis test fixtures that used product "sanitas" for a
// non-Ignis entry. The comments misstated which products hide the
// Ignis-only panels, and the fixtures exercised a product id the
// console no longer offers. Now every one of those reads Medicus,
// and this test guards that no retired Sanitas name creeps back
// into the Agent 1 web or native sources. The guard scans app
// sources only, not tests/ — this file itself names the retired
// product, and the two fixed fixtures are covered by their own
// suites still passing with a Medicus entry in the non-Ignis seat.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";

const root = new URL("..", import.meta.url).pathname;

function webSources() {
  const files = ["index.html", "styles.css", "logo-studio.html"];
  for (const entry of readdirSync(join(root, "js"))) {
    if (entry.endsWith(".js")) files.push(join("js", entry));
  }
  files.push(join("design", "meta-ascii-logo-studio.html"));
  return files;
}

function swiftSources() {
  const base = join(root, "native", "Sources");
  const out = [];
  const walk = (dir) => {
    for (const entry of readdirSync(dir, { withFileTypes: true })) {
      const path = join(dir, entry.name);
      if (entry.isDirectory()) walk(path);
      else if (entry.name.endsWith(".swift")) out.push(path);
    }
  };
  walk(base);
  return out;
}

test("no retired Sanitas name in Agent 1 web or native sources", () => {
  const offenders = [];
  for (const file of [...webSources(), ...swiftSources()]) {
    const text = readFileSync(file, "utf8");
    if (/sanitas/i.test(text)) offenders.push(file);
  }
  assert.deepEqual(offenders, [], "sources still naming Sanitas");
});

test("product switcher offers Vigiles, Ignis, Medicus — never Sanitas", () => {
  const products = readFileSync(join(root, "js", "products.js"), "utf8");
  for (const id of ["vigiles", "ignis", "medicus"]) {
    assert.match(products, new RegExp(`id: "${id}"`), `switcher offers ${id}`);
  }
  assert.doesNotMatch(products, /sanitas/i, "switcher never offers Sanitas");
});
