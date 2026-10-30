// Node built-in test runner, no dependencies:
//   node --test tests/latest-panel-shadow.test.mjs
//
// HANA Agent1: the Latest assessment panel's drop shadow — the web
// counterpart to the native UI-10 panel shadow, which casts black at
// 0.35, 8pt down, for all three products. The web theme blocks give
// Ignis and Medicus panels a shadow of
// 0 0 0 1px rgba(accent, 0.15), 0 8px 24px rgba(0, 0, 0, 0.35), but
// the base .panel carries no shadow and Vigiles has no theme panel
// shadow, so a shown assessment under Vigiles read flat while the
// native panel lifted off the page. Worse, a redisplayed assessment
// under Ignis or Medicus kept the SELECTED product's faint 1px
// accent ring from the theme shadow — a second, wrong-accent edge
// next to its own-accent border at 0.5. The fix adds the drop half
// only, 0 8px 24px rgba(0, 0, 0, 0.35), to the existing
// latest-product-<product> rules, which tie the theme rules'
// specificity and win on source order since they sit after them,
// so a shown assessment lifts in every selection and carries no
// faint ring at all: the own-accent border already draws the
// stronger edge, exactly the reason UI-10 omits the ring natively.
// The shadow is product-neutral black, so a switch cannot re-tint
// it, and it needs no assessment-own-accent treatment. No Swift
// toolchain exists in this sandbox, so these are static checks on
// the shipped CSS.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");

// The theme rules this must beat sit in the Medicus and Ignis blocks;
// the shadow rules must come after them to win the specificity tie
// on source order, exactly like the wash and border rules they extend.
const lastThemePanel = Math.max(
  css.lastIndexOf('body[data-product="medicus"] .panel {'),
  css.lastIndexOf('body[data-product="ignis"] .panel {'),
);
assert.ok(lastThemePanel > 0, "theme panel rules exist");

for (const product of ["vigiles", "ignis", "medicus"]) {
  test(`web: Latest panel shadow for ${product} is the product-neutral drop only`, () => {
    const rule = css.match(
      new RegExp(`body \\.panel\\.latest-product-${product} \\{[^}]*\\}`),
    );
    assert.ok(rule, `${product} panel rule exists`);
    assert.ok(
      css.indexOf(rule[0]) > lastThemePanel,
      `${product} rule sits after the theme panel rules, so it wins the tie`,
    );
    assert.match(
      rule[0],
      /box-shadow: 0 8px 24px rgba\(0, 0, 0, 0\.35\)/,
      "drop half of the theme shadow, black at 0.35, 8px down, 24px blur",
    );
    assert.doesNotMatch(
      rule[0],
      /0 0 0 1px/,
      "no faint 1px accent ring — the own-accent border at 0.5 is the edge",
    );
    assert.doesNotMatch(
      rule[0],
      /box-shadow:[^;]*var\(--accent\)/,
      "shadow is fixed black, not the selection accent",
    );
  });
}

test("web: Latest panel shadow is identical for all three products", () => {
  const shadows = ["vigiles", "ignis", "medicus"].map((product) => {
    const rule = css.match(
      new RegExp(`body \\.panel\\.latest-product-${product} \\{[^}]*\\}`),
    );
    assert.ok(rule, `${product} panel rule exists`);
    const shadow = rule[0].match(/box-shadow: [^;]+;/);
    assert.ok(shadow, `${product} rule carries a box-shadow`);
    return shadow[0];
  });
  assert.equal(shadows[1], shadows[0], "ignis shadow equals vigiles shadow");
  assert.equal(shadows[2], shadows[0], "medicus shadow equals vigiles shadow");
});

test("web: theme panel shadows are unchanged", () => {
  assert.match(
    css,
    /body\[data-product="ignis"\] \.panel \{[^}]*box-shadow: 0 0 0 1px rgba\(217, 43, 43, 0\.15\), 0 8px 24px rgba\(0, 0, 0, 0\.35\)/,
    "Ignis theme panel keeps its ring plus drop",
  );
  assert.match(
    css,
    /body\[data-product="medicus"\] \.panel \{[^}]*box-shadow: 0 0 0 1px rgba\(93, 168, 100, 0\.15\), 0 8px 24px rgba\(0, 0, 0, 0\.35\)/,
    "Medicus theme panel keeps its ring plus drop",
  );
});

test("web: Latest panel wash and border rules are untouched by the shadow", () => {
  const washes = {
    vigiles: "rgba(79, 126, 194, 0.09)",
    ignis: "rgba(217, 43, 43, 0.09)",
    medicus: "rgba(93, 168, 100, 0.09)",
  };
  const borders = {
    vigiles: "rgba(79, 126, 194, 0.5)",
    ignis: "rgba(217, 43, 43, 0.5)",
    medicus: "rgba(93, 168, 100, 0.5)",
  };
  for (const product of Object.keys(washes)) {
    const rule = css.match(
      new RegExp(`body \\.panel\\.latest-product-${product} \\{[^}]*\\}`),
    );
    assert.ok(rule, `${product} panel rule exists`);
    assert.match(
      rule[0],
      new RegExp(`background: linear-gradient\\(180deg, ${washes[product].replace(/[()]/g, "\\$&")}`),
      `${product} wash unchanged`,
    );
    assert.match(
      rule[0],
      new RegExp(`border-color: ${borders[product].replace(/[()]/g, "\\$&")}`),
      `${product} border unchanged`,
    );
  }
});
