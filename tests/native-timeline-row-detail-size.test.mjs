// Node built-in test runner, no dependencies:
//   node --test tests/native-timeline-row-detail-size.test.mjs
//
// IGNIS-UI-43 (Del UI push, Oct 29): native timeline row detail size
// parity. The web history body is a plain <p> in a .history-item, so
// it inherits the 15px body size — .history-item p sets only a
// margin, no font-size of its own — but the native TimelineView row
// detail used .callout (16pt), so it read one point larger than the
// web body line while the row product name and timestamp (UI-37)
// already matched their own 12.5px web rules. The fix gives the
// detail a 15pt system font, keeping its three-line limit, its
// wording (the assessment summary or the failure message), and the
// row's product-accent edge. No Swift toolchain exists in this
// sandbox, so these are static checks on the shipped Swift.

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

const detail = blockAfter("Text(item.detail)");

test("native timeline row detail: web contract — body at 15px, history body inherits it", () => {
  const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
  assert.match(
    css,
    /body \{\s+margin: 0;\s+background: var\(--bg\);\s+color: var\(--text\);\s+font-family: [^;]+;\s+font-size: 15px;/,
    "web body is 15px",
  );
  assert.match(
    css,
    /\.history-item p \{\s+margin: 2px 0;\s+\}/,
    "web history body sets no font-size of its own, so it inherits 15px",
  );
});

test("native timeline row detail: takes 15pt, no callout left", () => {
  assert.match(
    detail,
    /\.font\(\.system\(size: 15\)\)/,
    "detail takes 15pt",
  );
  assert.doesNotMatch(detail, /\.font\(\.callout\)/, "no callout left on detail");
});

test("native timeline row detail: keeps its three-line limit", () => {
  assert.match(detail, /\.lineLimit\(3\)/, "detail keeps lineLimit 3");
});

test("native timeline row detail: still renders the row's own detail text", () => {
  assert.match(
    timeline,
    /Text\(item\.detail\)/,
    "detail still renders item.detail",
  );
});
