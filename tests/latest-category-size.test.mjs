// Node built-in test runner, no dependencies:
//   node --test tests/latest-category-size.test.mjs
//
// HANA Agent1: the Latest panel's category at the native panel's
// title3 size. The native category is a title3 Text (20pt, bold),
// but the web category was a bare strong, so it read at the 15px
// body size — the panel's title did not stand out from its summary
// and observation text, while the native title stands above them.
// The fix gives the web category its own class at 20px, the 1:1
// pt-to-px mapping used by the 12.5pt subline (UI-19) and the 13pt
// uncertainty heading (UI-12). Weight comes from the strong element
// itself. No Swift toolchain exists in this sandbox, so the native
// side is checked statically on the shipped Swift.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
const swift = readFileSync(
  new URL(
    "../native/Sources/MetaTrio/Views/AssessmentView.swift",
    import.meta.url,
  ),
  "utf8",
);

test("web category: strong with class assessment-category, first in the head", () => {
  assert.match(
    app,
    /const type = document\.createElement\("strong"\);\s+type\.className = "assessment-category";\s+type\.textContent = assessment\.assessment\.category;/,
    "renderLatest tags the category strong with assessment-category",
  );
  const headAt = app.indexOf('head.className = "assessment-head"');
  const typeAt = app.indexOf('type.className = "assessment-category"');
  const productAt = app.indexOf('productEl.className = "assessment-product"');
  assert.ok(
    headAt > 0 && typeAt > headAt && productAt > typeAt,
    "category is created first in the head, before the product span",
  );
});

test("web .assessment-category rule: 20px, no weight override", () => {
  const rule = css.match(/\.assessment-category \{[^}]*\}/);
  assert.ok(rule, ".assessment-category rule exists");
  assert.match(rule[0], /font-size: 20px;/, "category reads at 20px (native title3)");
  assert.doesNotMatch(
    rule[0],
    /font-weight/,
    "weight stays the strong element's own bold, not a new rule",
  );
  assert.match(css, /body \{[^}]*font-size: 15px;/, "body size is 15px, so the old bare strong read smaller");
});

test("native category: title3, bold, unchanged", () => {
  assert.match(
    swift,
    /Text\(response\.assessment\.category\)\s+\.font\(\.title3\)\s+\.fontWeight\(\.bold\)/,
    "native category keeps title3 (20pt) bold",
  );
});

test("guards: product, timestamp, flag, and history titles unchanged", () => {
  assert.match(
    css,
    /\.assessment-product \{[^}]*font-size: 12\.5px;[^}]*font-weight: 700;/,
    "product name keeps 12.5px weight 700 (UI-19)",
  );
  assert.match(
    css,
    /\.assessment-time \{[^}]*font-size: 12\.5px;/,
    "timestamp keeps 12.5px (UI-19)",
  );
  assert.match(
    css,
    /\.review-flag \{[^}]*font-size: 12px;/,
    "review flag keeps 12px (UI-16)",
  );
  assert.doesNotMatch(
    css,
    /\.history-head strong \{[^}]*font-size/,
    "no history-head strong size rule: history titles keep body size",
  );
  assert.doesNotMatch(
    css,
    /(^|\n)strong \{[^}]*font-size/,
    "no bare strong size rule: only the assessment category grows",
  );
  assert.match(
    app,
    /const titleEl = document\.createElement\("strong"\);\s+titleEl\.textContent = title;/,
    "history title strong gains no assessment-category class",
  );
});
