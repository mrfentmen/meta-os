// Node built-in test runner, no dependencies:
//   node --test tests/latest-panel-wash.test.mjs
//
// HANA Agent1: the Latest assessment panel's wash follows the
// assessment's own product, not the selected product's — the web
// counterpart to the native UI-6 panel wash. The theme blocks wash
// every .panel in the SELECTED product's accent
// (body[data-product] .panel), so a past Ignis assessment shown again
// under Vigiles read flat (Vigiles has no panel gradient), and one
// shown under Medicus read green, while the native panel washed in
// the assessment's own accent at 0.09. The fix tags the Latest panel
// section in renderLatest with a latest-product-<product> class whose
// rule uses the same 0.09-at-the-top gradient shape with a fixed
// rgba accent, and clears the class on Reset. No Swift toolchain
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

const washes = {
  vigiles: "rgba(79, 126, 194, 0.09)",
  ignis: "rgba(217, 43, 43, 0.09)",
  medicus: "rgba(93, 168, 100, 0.09)",
};

// The theme rules this must beat sit in the Medicus and Ignis blocks;
// the wash rules must come after them to win the specificity tie on
// source order.
const lastThemePanel = Math.max(
  css.lastIndexOf('body[data-product="medicus"] .panel {'),
  css.lastIndexOf('body[data-product="ignis"] .panel {'),
);
assert.ok(lastThemePanel > 0, "theme panel rules exist");

for (const [product, rgba] of Object.entries(washes)) {
  test(`web: Latest panel wash for ${product} uses the fixed ${product} accent at 0.09`, () => {
    const rule = css.match(
      new RegExp(
        `body \\.panel\\.latest-product-${product} \\{[^}]*\\}`,
      ),
    );
    assert.ok(rule, `${product} panel-wash rule exists`);
    assert.match(
      rule[0],
      new RegExp(
        `background: linear-gradient\\(180deg, ${rgba.replace(
          /[()]/g,
          "\\$&",
        )}, var\\(--panel\\) 42%\\)`,
      ),
    );
    assert.doesNotMatch(
      rule[0],
      /var\(--accent\)/,
      "fixed rgba, not the selection accent, so a switch cannot re-tint it",
    );
    assert.ok(
      css.indexOf(rule[0]) > lastThemePanel,
      "wash rule sits after the theme panel rules, so it wins the specificity tie",
    );
  });

  test(`web: renderLatest tags a ${product} assessment's panel with its wash class`, () => {
    assert.match(
      render,
      new RegExp(
        `${product}: "latest-product-${product}"`,
      ),
      `${product} assessments map to the latest-product-${product} panel class`,
    );
  });
}

test("web: renderLatest clears a predecessor's wash before tagging the new one", () => {
  assert.match(
    render,
    /latestPanel\.classList\.remove\(\s+"latest-product-vigiles",\s+"latest-product-ignis",\s+"latest-product-medicus",\s+\);/,
    "stale wash classes are removed so a redisplayed assessment never keeps its predecessor's tint",
  );
});

test("web: only the three known products get a wash class (no invented color)", () => {
  const keys = render.match(/^\s+(vigiles|ignis|medicus): "latest-product-[a-z]+",/gm) || [];
  assert.deepEqual(keys.map((k) => k.trim()).sort(), [
    'ignis: "latest-product-ignis",',
    'medicus: "latest-product-medicus",',
    'vigiles: "latest-product-vigiles",',
  ]);
});

test("web: Reset clears the Latest panel wash class", () => {
  assert.match(
    appJs,
    /resetLatestPanel\.classList\.remove\(\s+"latest-product-vigiles",\s+"latest-product-ignis",\s+"latest-product-medicus",\s+\);/,
    "the cleared panel does not keep the last assessment's product tint",
  );
});

test("web: the selection panel gradients are untouched", () => {
  const medicus = css.match(
    /body\[data-product="medicus"\] \.panel \{[^}]*\}/,
  );
  assert.ok(medicus, "Medicus selection panel rule still exists");
  assert.match(medicus[0], /rgba\(93, 168, 100, 0\.09\)/);
  const ignis = css.match(/body\[data-product="ignis"\] \.panel \{[^}]*\}/);
  assert.ok(ignis, "Ignis selection panel rule still exists");
  assert.match(ignis[0], /rgba\(217, 43, 43, 0\.09\)/);
});
