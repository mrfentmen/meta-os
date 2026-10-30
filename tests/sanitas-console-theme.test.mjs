// Node built-in test runner, no dependencies:
//   node --test tests/sanitas-console-theme.test.mjs
//
// Sanitas ops-console pass (Del UI direction, Oct 29): modern, elite,
// professional dispatch-console feel on the web surface, Sanitas only.
// Static checks on the shipped CSS: uppercase section labels, mono
// status readout, sharper primary buttons, framed console readouts.
// Guardrail: the console block touches no disclosure, no limitations
// banner, no spinning background, no contract, no Spark gate.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
const marker = "/* Sanitas ops-console pass";
const consoleBlock = css.slice(css.indexOf(marker));
assert.notEqual(css.indexOf(marker), -1, "console block exists");

function sanitasRule(selector) {
  const rule = consoleBlock.match(
    new RegExp(`body\\[data-product="sanitas"\\] ${selector} \\{[^}]*\\}`),
  );
  assert.ok(rule, `Sanitas console rule exists: ${selector}`);
  return rule[0];
}

test("console: Sanitas panel headers are uppercase with console tracking", () => {
  const rule = sanitasRule("\\.panel h2");
  assert.match(rule, /text-transform: uppercase/);
  assert.match(rule, /letter-spacing: 0\.08em/);
});

test("console: Sanitas subheads are uppercase with console tracking", () => {
  const rule = sanitasRule("\\.subhead");
  assert.match(rule, /text-transform: uppercase/);
  assert.match(rule, /letter-spacing: 0\.06em/);
});

test("console: Sanitas status line reads in mono", () => {
  const rule = sanitasRule("\\.status");
  assert.match(rule, /font-family: var\(--mono\)/);
});

test("console: Sanitas primary buttons are sharper", () => {
  const rule = sanitasRule("\\.btn-primary");
  assert.match(rule, /border-radius: 3px/);
});

test("console: Sanitas latest-assessment readout is framed", () => {
  const rule = sanitasRule("\\.mono-block");
  assert.match(rule, /border: 1px solid rgba\(93, 168, 100, 0\.4\)/);
  assert.match(rule, /background: rgba\(0, 0, 0, 0\.25\)/);
});

test("console: block touches no disclosure, limitations, background, or Spark gate", () => {
  const rulesOnly = consoleBlock.replace(/\/\*[\s\S]*?\*\//g, "");
  for (const forbidden of ["limitations", "sampling-disclosure", "logo-background", "Spark", "assess"]) {
    assert.ok(!rulesOnly.includes(forbidden), `console block must not rule on ${forbidden}`);
  }
});
