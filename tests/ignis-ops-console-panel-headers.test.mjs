// Node built-in test runner, no dependencies:
//   node --test tests/ignis-ops-console-panel-headers.test.mjs
//
// OPS-CONSOLE-1 (Del UI direction, Oct 29): first web-first
// modern/elite/professional dispatch/ops-console piece for Ignis.
// Panel headings become console section labels — uppercase mono
// with wide tracking and a red accent tick — scoped to
// body[data-product="ignis"] only. Size and weight stay at the base
// 15px/700 (the base .panel h2 rule owns those), so native parity
// holds. No contract, server, or Spark-gate change; no live calls.
// The spinning ASCII background, disclosures, and limitations
// banner are untouched by this change.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");

function ignisPanelH2Rule() {
  const rule = css.match(
    /body\[data-product="ignis"\] \.panel h2 \{[^}]*\}/,
  );
  assert.ok(rule, "Ignis console panel-heading rule exists");
  return rule[0];
}

test("web: Ignis panel headings are uppercase mono console labels", () => {
  const rule = ignisPanelH2Rule();
  assert.match(rule, /font-family: var\(--mono\)/);
  assert.match(rule, /text-transform: uppercase/);
  assert.match(rule, /letter-spacing: 0\.12em/);
});

test("web: Ignis panel headings carry a red accent tick", () => {
  const rule = ignisPanelH2Rule();
  assert.match(rule, /border-left: 3px solid #d92b2b/);
  assert.match(rule, /padding-left: 10px/);
});

test("web: Ignis console headings keep base size and weight for native parity", () => {
  const rule = ignisPanelH2Rule();
  assert.doesNotMatch(rule, /font-size:/, "size stays at the base 15px");
  assert.doesNotMatch(rule, /font-weight:/, "weight stays at the base 700");
  assert.match(
    css,
    /\.panel h2 \{\s+margin: 0 0 10px;\s+font-size: 15px;\s+font-weight: 700;/,
    "base .panel h2 still owns 15px/700",
  );
});

test("web: console headings touch Ignis only, never another product", () => {
  // Sanitas legitimately carries its own panel-heading rule from
  // Milo's Sanitas ops-console pass, and Vigiles legitimately
  // carries its own from OPS-CONSOLE-6 (same direction, their
  // lanes); the Ignis rule must not itself restyle any other
  // product, and the Ignis block must not carry their colors.
  const rule = ignisPanelH2Rule();
  assert.doesNotMatch(rule, /#5da864/, "Ignis rule carries no Sanitas green");
  assert.doesNotMatch(rule, /#4f7ec2/, "Ignis rule carries no Vigiles blue");
  const block = css.slice(
    css.indexOf("/* OPS-CONSOLE-1"),
    css.indexOf("/* OPS-CONSOLE-6"),
  );
  assert.doesNotMatch(block, /#5da864/, "no Sanitas green in the console block");
  assert.doesNotMatch(block, /#4f7ec2/, "no Vigiles blue in the console block");
});
