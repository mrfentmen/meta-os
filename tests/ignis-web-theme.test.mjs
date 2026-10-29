// Node built-in test runner, no dependencies:
//   node --test tests/ignis-web-theme.test.mjs
//
// IGNIS-UI-3 (Del UI push, Oct 29): complete the Ignis web theme to
// mirror the Sanitas theme block, in Ignis red #d92b2b, scoped to
// body[data-product="ignis"] only. R2 landed only the panel gradient;
// UI-3 adds the topbar, product badge, primary button, chips, and
// switcher glow, plus the Ignis history edge (the M3 counterpart: an
// Ignis entry's edge uses the Ignis accent, not its status color).
// No Swift toolchain exists in this sandbox, so these are static
// checks on the shipped CSS and web client. No contract, server, or
// Spark-gate change; no live calls.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
const appJs = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");

function ignisRule(selector) {
  const rule = css.match(
    new RegExp(`body\\[data-product="ignis"\\] ${selector} \\{[^}]*\\}`),
  );
  assert.ok(rule, `Ignis rule exists: ${selector}`);
  return rule[0];
}

test("web: Ignis topbar carries a red gradient, scoped to Ignis only", () => {
  const rule = ignisRule("\\.topbar");
  assert.match(rule, /linear-gradient\(180deg, rgba\(217, 43, 43, 0\.16\)/);
  assert.match(rule, /border-bottom-color: var\(--accent\)/);
});

test("web: Ignis product badge carries a red gradient", () => {
  const rule = ignisRule("\\.product-badge");
  assert.match(rule, /linear-gradient\(135deg, #e54848, #b01e1e\)/);
  assert.match(rule, /box-shadow: 0 0 14px rgba\(217, 43, 43, 0\.45\)/);
});

test("web: Ignis primary button carries a red gradient", () => {
  const rule = ignisRule("\\.btn-primary:not\\(:disabled\\)");
  assert.match(rule, /linear-gradient\(135deg, #e54848, #b01e1e\)/);
  assert.match(rule, /box-shadow: 0 0 14px rgba\(217, 43, 43, 0\.35\)/);
});

test("web: Ignis chips are red-tinted", () => {
  const rule = ignisRule("\\.chip");
  assert.match(rule, /border-color: rgba\(217, 43, 43, 0\.55\)/);
  assert.match(rule, /background: rgba\(217, 43, 43, 0\.1\)/);
});

test("web: Ignis switcher option glows red when checked", () => {
  const rule = ignisRule(
    '\\.product-option\\[data-product-option="ignis"\\]:has\\(input:checked\\)',
  );
  assert.match(
    rule,
    /box-shadow: inset 0 0 0 1px #d92b2b, 0 0 14px rgba\(217, 43, 43, 0\.35\)/,
  );
});

test("web: Ignis history entries carry the Ignis accent edge", () => {
  const rule = css.match(
    /\.history-item\.history-product-ignis \{[^}]*\}/,
  );
  assert.ok(rule, "Ignis history edge rule exists");
  assert.match(rule[0], /border-left-color: #d92b2b/);
  assert.match(
    appJs,
    /else if \(entryProduct === "ignis"\) \{\s+item\.classList\.add\("history-product-ignis"\);/,
    "Ignis entries get the history-product-ignis class",
  );
});

test("web: Ignis theme uses no Sanitas green and never restyles Vigiles", () => {
  const ignisBlock = css.slice(css.indexOf("/* Ignis theme"));
  assert.doesNotMatch(ignisBlock, /#5da864/, "no Sanitas green in Ignis theme");
  assert.doesNotMatch(
    css,
    /body\[data-product="vigiles"\][^{]*\{[^}]*linear-gradient/,
    "Vigiles stays flat — no gradient rule under a Vigiles selector",
  );
});
