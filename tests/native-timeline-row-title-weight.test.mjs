// Node built-in test runner, no dependencies:
//   node --test tests/native-timeline-row-title-weight.test.mjs
//
// IGNIS-UI-55 (Del UI push, Oct 29): native timeline row title weight
// parity. The web history head renders its title as a strong element
// in a .history-head paragraph (js/app.js), and a strong element reads
// at weight 700 — but the native title used semibold (600), so it read
// one step lighter than the web title while the observation category
// (UI-17) already matched its own web strong at bold and the row title
// size (UI-53) already matched at 15pt. The fix gives the title a bold
// weight, keeping its 15pt size and its assessment-primary and
// failure-red colors. No Swift toolchain exists in this sandbox,
// so these are static checks on the shipped Swift.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const timeline = readFileSync(
  new URL("../native/Sources/MetaTrio/Views/TimelineView.swift", import.meta.url),
  "utf8",
);

function blockAfter(marker, length = 600) {
  const start = timeline.indexOf(marker);
  assert.ok(start >= 0, `${marker} exists`);
  return timeline.slice(start, start + length);
}

const title = blockAfter("Text(item.title)");

test("native timeline row title weight: web contract — history title is a strong element", () => {
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  assert.match(
    app,
    /head\.className = "history-head";/,
    "web history head carries class history-head",
  );
  assert.match(
    app,
    /const titleEl = document\.createElement\("strong"\);/,
    "web history title renders as a strong element in that head",
  );
  const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
  assert.doesNotMatch(
    css,
    /\.history-head\s*\{[^}]*font-weight/,
    "web .history-head sets no font-weight of its own, so the strong element keeps its 700 weight",
  );
});

test("native timeline row title weight: takes bold, keeps 15pt size and row colors", () => {
  assert.match(
    title,
    /Text\(item\.title\)\s+\.font\(\.system\(size: 15\)\)\s+\.fontWeight\(\.bold\)\s+\.foregroundStyle\(titleColor\(for: item\)\)/,
    "title takes bold weight at its UI-53 15pt size with titleColor",
  );
  assert.match(
    timeline,
    /case \.assessment:\s+return \.primary\s+case \.failure:\s+return \.red/,
    "titleColor still gives assessment rows primary and failure rows red",
  );
});

test("native timeline row title weight: row neighbors untouched", () => {
  const product = blockAfter("Text(item.product.config.displayName)");
  assert.match(
    product,
    /\.font\(\.system\(size: 12\.5\)\)/,
    "product name keeps its UI-37 12.5pt size",
  );
  const timestamp = blockAfter("Text(item.timestamp)");
  assert.match(
    timestamp,
    /\.font\(\.system\(size: 12\.5\)\)/,
    "timestamp keeps its UI-37 12.5pt size",
  );
  const detail = blockAfter("Text(item.detail)");
  assert.match(
    detail,
    /\.font\(\.system\(size: 15\)\)/,
    "detail keeps its UI-43 15pt size",
  );
  assert.match(
    detail,
    /\.lineLimit\(3\)/,
    "detail keeps its three-line limit",
  );
});

test("native timeline row title weight: row layout untouched", () => {
  assert.match(
    timeline,
    /HStack\(alignment: \.firstTextBaseline, spacing: 6\) \{/,
    "title row keeps its firstTextBaseline HStack",
  );
  assert.match(
    timeline,
    /\.padding\(\.leading, 10\)/,
    "row keeps its UI-4 10pt leading rule gap",
  );
});
