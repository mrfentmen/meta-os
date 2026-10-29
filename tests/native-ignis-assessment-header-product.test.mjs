// Node built-in test runner, no dependencies:
//   node --test tests/native-ignis-assessment-header-product.test.mjs
//
// HANA Agent1 (native UI-13, Oct 29): native latest-assessment panel
// header product-name parity. The web panel renders its product name
// with class "assessment-product" — 12.5px, weight 700, in the
// assessment's own product accent (fixed hex per product, falling back
// to the selected product's accent for an unknown key) — with the
// timestamp in the muted .assessment-time style. The native subline
// was one secondary caption, so a redisplayed Ignis assessment's
// product name read in the same gray as its timestamp while the web
// name read red and bold. The fix concatenates two Text segments: a
// secondary timestamp segment and a bold product segment tinted by
// the assessment-own accentColor, keeping the caption size and the
// timestamp-first order. No Swift toolchain exists in this sandbox,
// so these are static checks on the shipped Swift.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const assessment = readFileSync(
  new URL(
    "../native/Sources/MetaTrio/Views/AssessmentView.swift",
    import.meta.url,
  ),
  "utf8",
);

const headerFn = assessment.slice(
  assessment.indexOf("private var header"),
  assessment.indexOf("/// Display name for the product key"),
);
assert.ok(headerFn.length > 0, "header exists");

test("native header subline: timestamp muted, product bold in own accent, caption size", () => {
  assert.match(
    headerFn,
    /Text\("\\\(response\.timestamp\) · "\)\s+\.foregroundStyle\(\.secondary\)\s+\+ Text\(productDisplayName\)\s+\.fontWeight\(\.bold\)\s+\.foregroundStyle\(accentColor\)/,
    "subline concatenates a secondary timestamp segment and a bold own-accent product segment",
  );
  assert.match(
    headerFn,
    /\)\s+\.font\(\.caption\)/,
    "concatenated subline keeps the caption size",
  );
});

test("native header subline: no single secondary Text swallowing the product name", () => {
  assert.doesNotMatch(
    headerFn,
    /Text\("\\\(response\.timestamp\) · \\\(productDisplayName\)"\)/,
    "product name is no longer inside the plain secondary timestamp Text",
  );
});

test("native header subline: web contract — product bold in own accent, timestamp muted", () => {
  const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
  assert.match(
    css,
    /\.assessment-product \{\s+color: var\(--accent\);\s+font-size: 12\.5px;\s+font-weight: 700;/,
    "web product name is 12.5px, weight 700, in an accent color",
  );
  assert.match(
    css,
    /\.assessment-time \{\s+color: var\(--muted\);\s+font-size: 12\.5px;/,
    "web timestamp is 12.5px muted",
  );
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  assert.match(
    app,
    /productEl\.className = "assessment-product";/,
    "web product name carries the assessment-product class",
  );
  assert.match(
    assessment,
    /private var accentColor: Color/,
    "native panel already defines the assessment-own accent used by the product segment",
  );
});

test("native header: header combine trait kept, no selected product consulted", () => {
  assert.match(
    headerFn,
    /\.accessibilityElement\(children: \.combine\)/,
    "header stays one VoiceOver item",
  );
  assert.doesNotMatch(
    assessment,
    /selectedProduct/,
    "AssessmentView never consults the selected product",
  );
});
