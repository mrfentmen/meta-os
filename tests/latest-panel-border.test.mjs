// Node built-in test runner, no dependencies:
//   node --test tests/latest-panel-border.test.mjs
//
// HANA Agent1: the Latest assessment panel's border follows the
// assessment's own product, not the selected product's — the web
// counterpart to the native UI-9 panel border. The theme blocks
// border every .panel in the SELECTED product's accent
// (body[data-product] .panel), so a past Ignis assessment shown again
// under Medicus kept a Medicus-green border, and one shown under
// Vigiles kept the neutral panel border, while its wash and product
// name already read Ignis red and the native panel strokes its own
// accent at 0.5. The fix adds a border-color at 0.5 to the existing
// latest-product-<product> rules, in the same fixed rgba accent as
// the wash, so a switch cannot re-tint a shown assessment.
// Generalization, stated plainly: the web Vigiles theme carries no
// accent panel border, but the native UI-9 border strokes all three
// products in their own accent, so the web rule does the same for
// Vigiles rather than leaving its redisplayed panels border-neutral
// while Ignis and Medicus panels carry an accent edge. No Swift
// toolchain exists in this sandbox, so these are static checks on
// the shipped CSS.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");

// The theme rules this must beat sit in the Medicus and Ignis blocks;
// the border rules must come after them to win the specificity tie
// on source order, exactly like the wash rules they extend.
const lastThemePanel = Math.max(
  css.lastIndexOf('body[data-product="medicus"] .panel {'),
  css.lastIndexOf('body[data-product="ignis"] .panel {'),
);
assert.ok(lastThemePanel > 0, "theme panel rules exist");

const borders = {
  vigiles: "rgba(79, 126, 194, 0.5)",
  ignis: "rgba(217, 43, 43, 0.5)",
  medicus: "rgba(93, 168, 100, 0.5)",
};

for (const [product, rgba] of Object.entries(borders)) {
  test(`web: Latest panel border for ${product} uses the fixed ${product} accent at 0.5`, () => {
    const rule = css.match(
      new RegExp(`body \\.panel\\.latest-product-${product} \\{[^}]*\\}`),
    );
    assert.ok(rule, `${product} panel rule exists`);
    assert.match(
      rule[0],
      new RegExp(
        `border-color: ${rgba.replace(/[()]/g, "\\$&")}`,
      ),
    );
    assert.doesNotMatch(
      rule[0],
      /var\(--accent\)/,
      "fixed rgba, not the selection accent, so a switch cannot re-tint it",
    );
    assert.ok(
      css.indexOf(rule[0]) > lastThemePanel,
      "border rule sits after the theme panel rules, so it wins the specificity tie",
    );
  });
}

test("web: Latest panel borders match the theme panel borders for Ignis and Medicus", () => {
  const ignisTheme = css.match(
    /body\[data-product="ignis"\] \.panel \{[^}]*border-color: rgba\(217, 43, 43, 0\.5\)/,
  );
  assert.ok(ignisTheme, "Ignis theme panel border is rgba(217, 43, 43, 0.5)");
  const medicusTheme = css.match(
    /body\[data-product="medicus"\] \.panel \{[^}]*border-color: rgba\(93, 168, 100, 0\.5\)/,
  );
  assert.ok(medicusTheme, "Medicus theme panel border is rgba(93, 168, 100, 0.5)");
});

// Superseded in part by the UI-10 shadow slice: these rules now DO
// carry a box-shadow — the product-neutral drop, governed by
// tests/latest-panel-shadow.test.mjs (drop only, no faint ring,
// identical across products). What this test still guards is that
// the border slice added no SECOND wash; the shadow assertion moved
// to that file rather than being dropped.
test("web: Latest panel border adds no second wash", () => {
  for (const product of Object.keys(borders)) {
    const rule = css.match(
      new RegExp(`body \\.panel\\.latest-product-${product} \\{[^}]*\\}`),
    );
    assert.ok(rule, `${product} panel rule exists`);
    const backgrounds = rule[0].match(/background:/g) || [];
    assert.equal(backgrounds.length, 1, "exactly one background — the wash");
  }
});
