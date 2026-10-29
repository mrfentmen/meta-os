// Node built-in test runner, no dependencies:
//   node --test tests/native-ignis-header.test.mjs
//
// IGNIS-R2 (Del UI push, Oct 29): red identity in the native header,
// plus the matching web panel gradient. The native header's accent dot
// is shared across products, so Ignis gets its own flame chip in the
// identity row, gated on the selected product being Ignis, and the
// limitations box gets an accent leading rule — red on Ignis — matching
// the web .limitations border-left in --accent, which R1 already turned
// red for Ignis. On the web, the Ignis panel mirrors the Sanitas M3
// panel treatment in Ignis red #d92b2b, scoped to
// body[data-product="ignis"] only. No Swift toolchain exists in this
// sandbox, so these are static checks on the shipped Swift and CSS.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const contentView = readFileSync(
  new URL("../native/Sources/MetaTrio/Views/ContentView.swift", import.meta.url),
  "utf8",
);
const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");

const headerView = contentView.slice(
  contentView.indexOf("private struct HeaderView"),
  contentView.indexOf("// MARK: - Camera panel"),
);
assert.ok(headerView.length > 0, "HeaderView slice exists");

test("native header: Ignis-only flame chip in the identity row", () => {
  assert.match(
    headerView,
    /if model\.selectedProduct == \.ignis \{\s+Label\("Flame", systemImage: "flame\.fill"\)/,
    "flame chip is gated on Ignis and uses the flame symbol",
  );
  assert.match(
    headerView,
    /Label\("Flame", systemImage: "flame\.fill"\)[\s\S]*?\.foregroundStyle\(accentColor\)/,
    "flame chip is tinted with the product accent (red on Ignis)",
  );
});

test("native header: limitations box carries an accent leading rule", () => {
  const limitations = headerView.slice(
    headerView.indexOf('Text(model.config.limitations)'),
  );
  assert.match(
    limitations,
    /\.overlay\(alignment: \.leading\) \{\s+Rectangle\(\)\s+\.fill\(accentColor\)\s+\.frame\(width: 3\)/,
    "limitations box has a 3pt accent leading rule, matching the web limitations border",
  );
});

test("web: Ignis panel carries a red gradient, scoped to Ignis only", () => {
  const panelRule = css.match(
    /body\[data-product="ignis"\] \.panel \{[^}]*\}/,
  );
  assert.ok(panelRule, "Ignis panel rule exists");
  assert.match(panelRule[0], /linear-gradient\(180deg, rgba\(217, 43, 43, 0\.09\)/);
  assert.match(panelRule[0], /border-color: rgba\(217, 43, 43, 0\.5\)/);
  assert.doesNotMatch(
    css,
    /body\[data-product="vigiles"\][^{]*\{[^}]*linear-gradient/,
    "Vigiles stays flat — no gradient rule under a Vigiles selector",
  );
  assert.doesNotMatch(
    css,
    /body\[data-product="ignis"\] \.panel \{[^}]*#5da864/,
    "Ignis panel gradient uses no Sanitas green",
  );
});
