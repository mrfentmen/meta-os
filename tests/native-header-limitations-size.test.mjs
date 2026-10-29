// Node built-in test runner, no dependencies:
//   node --test tests/native-header-limitations-size.test.mjs
//
// IGNIS-UI-27 (Del UI push, Oct 29): native header limitations size
// parity. The web frontend carries its per-product limitations notice
// as <p id="product-limitations" class="note"> — styles.css sets
// .note at 13px in --muted — but the native header's equivalent
// notice used .caption (12pt), so it read one point smaller than the
// web notice while the Latest-panel notes (UI-21) and the still-image
// and video intros (UI-25, UI-26) already matched their own 13px web
// rules. The fix gives the limitations notice a 13pt system font,
// keeping its muted color, wrapping, padding, background, and the
// accent leading rule. No Swift toolchain exists in this sandbox, so
// these are static checks on the shipped Swift.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const content = readFileSync(
  new URL(
    "../native/Sources/MetaTrio/Views/ContentView.swift",
    import.meta.url,
  ),
  "utf8",
);

const limitationsStart = content.indexOf("Text(model.config.limitations)");
assert.ok(limitationsStart >= 0, "limitations notice exists");
const limitations = content.slice(limitationsStart, limitationsStart + 1500);
assert.ok(limitations.length > 0, "limitations block exists");

test("native header limitations: web contract — .note at 13px muted", () => {
  const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
  assert.match(
    css,
    /\.note \{\s+color: var\(--muted\);\s+font-size: 13px;/,
    "web .note is 13px muted",
  );
});

test("native header limitations: web notice carries the note class", () => {
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.match(
    html,
    /<p id="product-limitations" class="note"/,
    "web product-limitations carries class note",
  );
});

test("native header limitations: notice takes the 13pt system font", () => {
  assert.match(
    limitations,
    /Text\(model\.config\.limitations\)\s+\.font\(\.system\(size: 13\)\)/,
    "limitations notice takes the 13pt font",
  );
});

test("native header limitations: no caption left, box unchanged", () => {
  const block = limitations.slice(0, limitations.indexOf(".clipShape"));
  assert.doesNotMatch(
    block,
    /\.font\(\.caption\)/,
    "no caption font left on the limitations notice",
  );
  assert.match(
    block,
    /\.foregroundStyle\(\.secondary\)/,
    "limitations notice keeps its muted color",
  );
  assert.match(
    block,
    /\.fixedSize\(horizontal: false, vertical: true\)/,
    "limitations notice keeps its wrapping",
  );
  assert.match(
    block,
    /\.overlay\(alignment: \.leading\)/,
    "limitations notice keeps its accent leading rule",
  );
});
