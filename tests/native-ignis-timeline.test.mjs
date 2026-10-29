// Node built-in test runner, no dependencies:
//   node --test tests/native-ignis-timeline.test.mjs
//
// IGNIS-UI-4 (Del UI push, Oct 29): native timeline product-accent edge
// parity with the web history edge. The web history items carry a 3px
// border-left in the entry's own product accent (Ignis red #d92b2b via
// .history-product-ignis), regardless of which product is selected and
// regardless of the entry kind. The native TimelineView rows carried no
// accent marker at all, so the fix adds a 3pt leading rule to every row
// in the row's own product accent, mirroring the R2 limitations-rule
// pattern. No Swift toolchain exists in this sandbox, so these are
// static checks on the shipped Swift.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const timeline = readFileSync(
  new URL("../native/Sources/MetaTrio/Views/TimelineView.swift", import.meta.url),
  "utf8",
);
const productConfig = readFileSync(
  new URL(
    "../native/Sources/MetaTrio/Models/ProductConfig.swift",
    import.meta.url,
  ),
  "utf8",
);

const rowFn = timeline.slice(timeline.indexOf("private func row(for item"));
assert.ok(rowFn.length > 0, "row(for:) exists");

test("native timeline: every row carries a 3pt accent leading rule", () => {
  const content = rowFn.slice(0, rowFn.indexOf("switch item.kind"));
  assert.match(
    content,
    /\.overlay\(alignment: \.leading\) \{\s+Rectangle\(\)\s+\.fill\(accentColor\(for: item\.product\)\)\s+\.frame\(width: 3\)/,
    "content (shared by both row kinds) has a 3pt leading rule in the row product accent",
  );
  assert.match(
    content,
    /\.padding\(\.leading, 10\)/,
    "rule sits in leading padding, mirroring the web history 10px text offset",
  );
});

test("native timeline: rule color comes from the row's own product, not the selection", () => {
  assert.doesNotMatch(
    rowFn,
    /accentColor\(for: item\.product\)[\s\S]*model\.selectedProduct/,
    "row accent does not consult the selected product",
  );
  const helper = timeline.slice(timeline.indexOf("private func accentColor(for product"));
  assert.ok(helper.length > 0, "accentColor(for:) helper exists");
  assert.match(
    helper,
    /switch product\.config\.accentColorName \{\s+case "blue": return \.blue\s+case "red": return \.red\s+case "green": return \.green/,
    "helper maps the row product's accentColorName, same mapping as ContentView",
  );
});

test("native timeline: Ignis rows resolve to red", () => {
  const ignis = productConfig.slice(productConfig.indexOf("static let ignis"));
  assert.match(
    ignis,
    /accentColorName: "red"/,
    "Ignis accentColorName is red (R1), so Ignis timeline rules are red",
  );
});

test("native timeline: rule is not confined to one row kind", () => {
  const switchBlock = rowFn.slice(rowFn.indexOf("switch item.kind"));
  assert.doesNotMatch(
    switchBlock,
    /Rectangle\(\)/,
    "no second rule inside the kind switch — the shared content rule covers both kinds",
  );
});
