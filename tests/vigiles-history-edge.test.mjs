// Node built-in test runner, no dependencies:
//   node --test tests/vigiles-history-edge.test.mjs
//
// HANA Agent1: the Vigiles history edge, completing the product-accent
// set M3 (Sanitas) and IGNIS-UI-3 (Ignis) started. A Vigiles entry's
// edge uses the Vigiles product accent #4f7ec2, not its status color,
// matching the native timeline rows, which carry their own product's
// accent for all three products (UI-4). Without it the web Vigiles
// entries kept status edges while the native Vigiles rows showed the
// blue product edge, so the two surfaces disagreed on exactly the
// default product's rows. No Swift toolchain exists in this sandbox,
// so these are static checks on the shipped CSS and web client.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
const appJs = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");

test("web: Vigiles history entries carry the Vigiles accent edge", () => {
  const rule = css.match(
    /\.history-item\.history-product-vigiles \{[^}]*\}/,
  );
  assert.ok(rule, "Vigiles history edge rule exists");
  assert.match(rule[0], /border-left-color: #4f7ec2/);
  assert.match(
    appJs,
    /else if \(entryProduct === "vigiles"\) \{\s+item\.classList\.add\("history-product-vigiles"\);/,
    "Vigiles entries get the history-product-vigiles class",
  );
});

test("web: Vigiles history edge uses a fixed accent, not the selection accent", () => {
  // --accent follows the currently selected product, so a rule built on
  // it would re-tint every Vigiles entry whenever the user switches
  // products. The Sanitas and Ignis rules use fixed hex for the same
  // reason; the Vigiles rule must too.
  const rule = css.match(
    /\.history-item\.history-product-vigiles \{[^}]*\}/,
  );
  assert.ok(rule, "Vigiles history edge rule exists");
  assert.doesNotMatch(rule[0], /var\(--accent\)/);
});

test("web: Sanitas and Ignis history edges are untouched by the Vigiles branch", () => {
  const sanitas = css.match(
    /\.history-item\.history-product-sanitas \{[^}]*\}/,
  );
  assert.ok(sanitas, "Sanitas history edge rule still exists");
  assert.match(sanitas[0], /border-left-color: #5da864/);
  const ignis = css.match(
    /\.history-item\.history-product-ignis \{[^}]*\}/,
  );
  assert.ok(ignis, "Ignis history edge rule still exists");
  assert.match(ignis[0], /border-left-color: #d92b2b/);
  assert.match(
    appJs,
    /if \(entryProduct === "sanitas"\) \{\s+item\.classList\.add\("history-product-sanitas"\);/,
    "Sanitas branch still first",
  );
  assert.match(
    appJs,
    /else if \(entryProduct === "ignis"\) \{\s+item\.classList\.add\("history-product-ignis"\);/,
    "Ignis branch still present",
  );
});
