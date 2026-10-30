// Node built-in test runner, no dependencies:
//   node --test tests/vigiles-ops-console.test.mjs
//
// OPS-CONSOLE-6 (Del UI direction, Oct 29): third web-first
// dispatch/ops-console piece, extending the direction Milo's
// Medicus pass set and OPS-CONSOLE-1/3 carried to Ignis, to the
// last product without it — Vigiles, in Vigiles blue: console
// panel headings, wider subhead tracking, mono status readout,
// sharper primary buttons, framed latest-assessment readout.
// Static checks on the shipped CSS, scoped to
// body[data-product="vigiles"] only.
// Guardrails: no Ignis red, no Medicus green, no Ignis or Medicus
// restyle, no disclosure / limitations / background / contract /
// Spark-gate rule, and blue never restyles a status color.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
const marker = "/* OPS-CONSOLE-6";
const consoleBlock = css.slice(css.indexOf(marker));
assert.notEqual(css.indexOf(marker), -1, "console block exists");

function vigilesRule(selector) {
  const rule = consoleBlock.match(
    new RegExp(`body\\[data-product="vigiles"\\] ${selector} \\{[^}]*\\}`),
  );
  assert.ok(rule, `Vigiles console rule exists: ${selector}`);
  return rule[0];
}

test("console: Vigiles panel headings are uppercase mono console labels", () => {
  const rule = vigilesRule("\\.panel h2");
  assert.match(rule, /font-family: var\(--mono\)/);
  assert.match(rule, /text-transform: uppercase/);
  assert.match(rule, /letter-spacing: 0\.12em/);
  assert.match(rule, /border-left: 3px solid #4f7ec2/);
  assert.match(rule, /padding-left: 10px/);
  assert.doesNotMatch(rule, /font-size:/, "size stays at the base 15px");
  assert.doesNotMatch(rule, /font-weight:/, "weight stays at the base 700");
});

test("console: Vigiles subheads widen to console tracking", () => {
  const rule = vigilesRule("\\.subhead");
  assert.match(rule, /letter-spacing: 0\.08em/);
  assert.doesNotMatch(rule, /font-size:/, "size stays at the base rule");
  assert.doesNotMatch(rule, /font-weight:/, "weight stays at the base rule");
  assert.doesNotMatch(rule, /color:/, "color stays at the base rule");
});

test("console: Vigiles status line reads in mono", () => {
  const rule = vigilesRule("\\.status");
  assert.match(rule, /font-family: var\(--mono\)/);
  assert.match(rule, /letter-spacing: 0\.02em/);
  assert.doesNotMatch(rule, /color:/, "blue never becomes a status color");
});

test("console: Vigiles primary buttons are sharper", () => {
  const rule = vigilesRule("\\.btn-primary");
  assert.match(rule, /border-radius: 3px/);
});

test("console: Vigiles latest-assessment readout is framed in Vigiles blue", () => {
  const rule = vigilesRule("\\.mono-block");
  assert.match(rule, /border: 1px solid rgba\(79, 126, 194, 0\.4\)/);
  assert.match(rule, /background: rgba\(0, 0, 0, 0\.25\)/);
});

test("console: block touches no other product and no guarded surface", () => {
  assert.doesNotMatch(consoleBlock, /#d92b2b/, "no Ignis red");
  assert.doesNotMatch(consoleBlock, /#5da864/, "no Medicus green");
  assert.doesNotMatch(
    consoleBlock,
    /body\[data-product="ignis"\]/,
    "no Ignis restyle",
  );
  assert.doesNotMatch(
    consoleBlock,
    /body\[data-product="medicus"\]/,
    "no Medicus restyle",
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
