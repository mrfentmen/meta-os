// Node built-in test runner, no dependencies:
//   node --test tests/native-camera-facing-note-size.test.mjs
//
// IGNIS-UI-28 (Del UI push, Oct 29): native camera facing note size
// parity.
// HN4-5 UPDATE (2026-11-01): the Swift note tests are stripped —
// the native camera panel's facing note was deleted with the
// WKWebView rewrite, so the Swift assertions no longer exist
// anywhere. The web contract tests below are kept verbatim.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

test("native camera facing note: web contract — .note at 13px muted", () => {
  const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
  assert.match(
    css,
    /\.note \{\s+color: var\(--muted\);\s+font-size: 13px;/,
    "web .note is 13px muted",
  );
});

test("native camera facing note: web note carries the note class", () => {
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.match(
    html,
    /<p class="note">A preference, not a requirement:/,
    "web camera-facing note carries class note",
  );
});
