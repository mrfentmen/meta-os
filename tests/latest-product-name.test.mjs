// Node built-in test runner, no dependencies:
//   node --test tests/latest-product-name.test.mjs
//
// HANA Agent1: the Latest assessment panel's product name keeps the
// assessment's own product accent, not the selected product's. The
// base .assessment-product rule uses var(--accent), which follows the
// current selection, so a past assessment shown again under another
// product read its product name in the wrong product's color — and a
// fresh assessment could land tinted wrong if the user switched
// products while its request was in flight. The history entries
// already fixed this for their edges (M3, IGNIS-UI-3, Vigiles edge)
// and the native panel fixed it for its leading rule (UI-5); the web
// Latest panel's product name was the remaining place where an
// assessment's identity re-tinted on a switch. No Swift toolchain
// exists in this sandbox, so these are static checks on the shipped
// CSS and web client.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
const appJs = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
const render = appJs.slice(
  appJs.indexOf("function renderLatest"),
  appJs.indexOf("function addHistoryItem"),
);
assert.ok(render.length > 0, "renderLatest exists");

const accents = {
  vigiles: "#4f7ec2",
  ignis: "#d92b2b",
  medicus: "#5da864",
};

for (const [product, hex] of Object.entries(accents)) {
  test(`web: Latest panel product name for ${product} uses the fixed ${product} accent`, () => {
    const rule = css.match(
      new RegExp(
        `\\.assessment-product\\.assessment-product-${product} \\{[^}]*\\}`,
      ),
    );
    assert.ok(rule, `${product} product-name rule exists`);
    assert.match(rule[0], new RegExp(`color: ${hex}`));
    assert.doesNotMatch(
      rule[0],
      /var\(--accent\)/,
      "fixed hex, not the selection accent, so a switch cannot re-tint it",
    );
  });

  test(`web: renderLatest tags a ${product} assessment with its product-name class`, () => {
    assert.match(
      render,
      new RegExp(
        `if \\(assessment\\.product === "${product}"\\) \\{\\s+productEl\\.classList\\.add\\("assessment-product-${product}"\\);`,
      ),
      `${product} assessments get the assessment-product-${product} class`,
    );
  });
}

test("web: an unknown product keeps the base selection accent (no invented color)", () => {
  // Only the three known products get a class branch in renderLatest;
  // anything else falls through to the base .assessment-product rule.
  const branches = render.match(/assessment\.product === "[a-z]+"/g) || [];
  assert.deepEqual(branches.sort(), [
    'assessment.product === "ignis"',
    'assessment.product === "medicus"',
    'assessment.product === "vigiles"',
  ]);
});

test("web: the base product-name rule is untouched", () => {
  const base = css.match(/\.assessment-product \{[^}]*\}/);
  assert.ok(base, "base rule exists");
  assert.match(base[0], /color: var\(--accent\)/);
});
