// Node built-in test runner, no dependencies:
//   node --test tests/native-timeline-row-title-size.test.mjs
//
// IGNIS-UI-53 (Del UI push, Oct 29): native timeline row title size
// parity. The web history head renders its title as a strong element
// in a .history-head paragraph (js/app.js), and styles.css gives that
// head no font-size of its own, so the title inherits the 15px body
// size — but the native title carried no font at all, so it read at
// the default 17pt body size, two points larger than the web title,
// while the row product name and timestamp (UI-37) already matched
// their own 12.5px web rules and the row detail (UI-43) already
// matched its own 15px web rule. The fix gives the title a 15pt
// system font, keeping its bold weight (UI-55) and its assessment-primary
// and failure-red colors. No Swift toolchain exists in this sandbox,
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

test("native timeline row title: web contract — history head strong on a 15px line", () => {
  const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
  assert.match(
    css,
    /body \{\s+margin: 0;\s+background: var\(--bg\);\s+color: var\(--text\);\s+font-family: [^;]+;\s+font-size: 15px;/,
    "web body is 15px",
  );
  assert.doesNotMatch(
    css,
    /\.history-head\s*\{[^}]*font-size/,
    "web .history-head sets no font-size of its own, so the title inherits the 15px body size",
  );
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
});

test("native timeline row title: takes 15pt, keeps bold weight and row colors", () => {
  assert.match(
    title,
    /Text\(item\.title\)\s+\.font\(\.system\(size: 15\)\)\s+\.fontWeight\(\.bold\)\s+\.foregroundStyle\(titleColor\(for: item\)\)/,
    "title takes 15pt and keeps its UI-55 bold weight and titleColor",
  );
  assert.match(
    timeline,
    /case \.assessment:\s+return \.primary\s+case \.failure:\s+return \.red/,
    "titleColor still gives assessment rows primary and failure rows red",
  );
});

test("native timeline row title: row neighbors untouched", () => {
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

test("native timeline row title: row layout untouched", () => {
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
