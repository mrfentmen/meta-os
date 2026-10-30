// Node built-in test runner, no dependencies:
//   node --test tests/ignis-ops-console-body.test.mjs
//
// OPS-CONSOLE-3 (Del UI direction, Oct 29): second web-first
// dispatch/ops-console piece for Ignis, extending OPS-CONSOLE-1's
// panel headings to the rest of the console surface — the same four
// elements Milo's Sanitas ops-console pass treated, in Ignis terms:
// wider subhead tracking, mono status readout, sharper primary
// buttons, framed latest-assessment readout. Static checks on the
// shipped CSS, scoped to body[data-product="ignis"] only.
// Guardrails: no Sanitas green, no Vigiles blue, no Vigiles or
// Sanitas restyle, no disclosure / limitations / background /
// contract / Spark-gate rule, and red never restyles a status color.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
const marker = "/* OPS-CONSOLE-3";
const consoleBlock = css.slice(css.indexOf(marker));
assert.notEqual(css.indexOf(marker), -1, "console block exists");

function ignisRule(selector) {
  const rule = consoleBlock.match(
    new RegExp(`body\\[data-product="ignis"\\] ${selector} \\{[^}]*\\}`),
  );
  assert.ok(rule, `Ignis console rule exists: ${selector}`);
  return rule[0];
}

test("console: Ignis subheads widen to console tracking", () => {
  const rule = ignisRule("\\.subhead");
  assert.match(rule, /letter-spacing: 0\.08em/);
  assert.doesNotMatch(rule, /font-size:/, "size stays at the base rule");
  assert.doesNotMatch(rule, /font-weight:/, "weight stays at the base rule");
  assert.doesNotMatch(rule, /color:/, "color stays at the base rule");
});

test("console: Ignis status line reads in mono", () => {
  const rule = ignisRule("\\.status");
  assert.match(rule, /font-family: var\(--mono\)/);
  assert.match(rule, /letter-spacing: 0\.02em/);
  assert.doesNotMatch(rule, /color:/, "red never becomes a status color");
});

test("console: Ignis primary buttons are sharper", () => {
  const rule = ignisRule("\\.btn-primary");
  assert.match(rule, /border-radius: 3px/);
});

test("console: Ignis latest-assessment readout is framed in Ignis red", () => {
  const rule = ignisRule("\\.mono-block");
  assert.match(rule, /border: 1px solid rgba\(217, 43, 43, 0\.4\)/);
  assert.match(rule, /background: rgba\(0, 0, 0, 0\.25\)/);
});

test("console: block touches no other product and no guarded surface", () => {
  assert.doesNotMatch(consoleBlock, /#5da864/, "no Sanitas green");
  assert.doesNotMatch(consoleBlock, /#4f7ec2/, "no Vigiles blue");
  assert.doesNotMatch(
    consoleBlock,
    /body\[data-product="vigiles"\]/,
    "no Vigiles restyle",
  );
  assert.doesNotMatch(
    consoleBlock,
    /body\[data-product="sanitas"\]/,
    "no Sanitas restyle",
  );
  const rulesOnly = consoleBlock.replace(/\/\*[\s\S]*?\*\//g, "");
  for (const forbidden of [
    "limitations",
    "sampling-disclosure",
    "logo-background",
    "Spark",
    "assess",
  ]) {
    assert.ok(
      !rulesOnly.includes(forbidden),
      `console block must not rule on ${forbidden}`,
    );
  }
});

test("console: OPS-CONSOLE-1 Ignis panel headings still present", () => {
  assert.match(
    css,
    /body\[data-product="ignis"\] \.panel h2 \{\s+font-family: var\(--mono\);/,
    "OPS-CONSOLE-1 headings intact",
  );
});
