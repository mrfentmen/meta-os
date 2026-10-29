// Node built-in test runner, no dependencies:
//   node --test tests/native-timeline-row-meta-size.test.mjs
//
// IGNIS-UI-37 (Del UI push, Oct 29): native timeline row product-name
// and timestamp size parity. The web assessment head carries its
// product name as .assessment-product at 12.5px and its timestamp as
// .assessment-time at 12.5px — but the native TimelineView row's
// product name and timestamp both used .caption (12pt), so they read
// a half point smaller than the web head's product and time while the
// timeline title (UI-34) already matched its own 15px web rule. The
// fix gives both a 12.5pt system font, keeping their muted color, the
// title's semibold weight, and the row detail's callout size. No Swift
// toolchain exists in this sandbox, so these are static checks on the
// shipped Swift.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const timeline = readFileSync(
  new URL("../native/Sources/MetaTrio/Views/TimelineView.swift", import.meta.url),
  "utf8",
);

function blockAfter(marker, length = 400) {
  const start = timeline.indexOf(marker);
  assert.ok(start >= 0, `${marker} exists`);
  return timeline.slice(start, start + length);
}

const product = blockAfter("Text(item.product.config.displayName)");
const timestamp = blockAfter("Text(item.timestamp)");

test("native timeline row product: web contract — .assessment-product at 12.5px", () => {
  const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
  assert.match(
    css,
    /\.assessment-product \{\s+color: var\(--accent\);\s+font-size: 12\.5px;/,
    "web .assessment-product is 12.5px",
  );
});

test("native timeline row timestamp: web contract — .assessment-time at 12.5px", () => {
  const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
  assert.match(
    css,
    /\.assessment-time \{\s+color: var\(--muted\);\s+font-size: 12\.5px;/,
    "web .assessment-time is 12.5px",
  );
});

test("native timeline row product: takes 12.5pt, keeps muted color", () => {
  assert.match(
    product,
    /\.font\(\.system\(size: 12\.5\)\)/,
    "product name takes 12.5pt",
  );
  assert.doesNotMatch(product, /\.font\(\.caption\)/, "no caption left on product name");
  assert.match(
    product,
    /\.foregroundStyle\(\.secondary\)/,
    "product name keeps muted color",
  );
});

test("native timeline row timestamp: takes 12.5pt, keeps muted color", () => {
  assert.match(
    timestamp,
    /\.font\(\.system\(size: 12\.5\)\)/,
    "timestamp takes 12.5pt",
  );
  assert.doesNotMatch(timestamp, /\.font\(\.caption\)/, "no caption left on timestamp");
  assert.match(
    timestamp,
    /\.foregroundStyle\(\.secondary\)/,
    "timestamp keeps muted color",
  );
});
