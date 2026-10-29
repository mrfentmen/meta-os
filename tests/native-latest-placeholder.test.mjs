// Node built-in test runner, no dependencies:
//   node --test tests/native-latest-placeholder.test.mjs
//
// UI-24: native Latest-panel placeholder size/face parity. The web
// frontend's Latest panel renders its waiting, error, and
// no-assessment strings as the direct text of #latest-assessment,
// which always carries class mono-block — styles.css sets
// .mono-block at 13px in the ui-monospace stack — but the native
// rightColumn rendered all three placeholders as plain Text at the
// default body size in the default face, so they read larger and
// non-mono while the assessment itself already matched its own web
// rules. The fix gives all three placeholders a 13pt monospaced
// system font, keeping each one's color, wrapping, and wording, and
// the waiting row's combined VoiceOver label. No Swift toolchain
// exists in this sandbox, so these are static checks on the shipped
// Swift.

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

const rightColumn = content.slice(
  content.indexOf("private var rightColumn"),
  content.indexOf("TimelineView(model: model)"),
);
assert.ok(rightColumn.length > 0, "rightColumn exists");

const monoFont = String.raw`\.font\(\.system\(size: 13, design: \.monospaced\)\)`;

test("native latest placeholder: web contract — #latest-assessment is mono-block 13px", () => {
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.ok(
    html.includes(`<div id="latest-assessment" class="mono-block"`),
    "web latest container carries mono-block",
  );
  const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
  assert.match(
    css,
    /\.mono-block \{\s+font-family: var\(--mono\);\s+font-size: 13px;/,
    "web .mono-block is 13px in the mono stack",
  );
});

test("native latest placeholder: waiting text takes the 13pt mono font", () => {
  assert.match(
    rightColumn,
    new RegExp(
      String.raw`Text\("Waiting for the first assessment…"\)\s+` + monoFont,
    ),
    "waiting text takes the 13pt mono font",
  );
});

test("native latest placeholder: backend-error text takes the 13pt mono font", () => {
  assert.match(
    rightColumn,
    new RegExp(
      String.raw`case \.error\(let message\) = model\.backendStatus \{\s+Text\(message\)\s+` +
        monoFont,
    ),
    "error text takes the 13pt mono font",
  );
});

test("native latest placeholder: no-assessment text takes the 13pt mono font", () => {
  assert.match(
    rightColumn,
    new RegExp(
      String.raw`Text\("No assessment received yet\."\)\s+` + monoFont,
    ),
    "no-assessment text takes the 13pt mono font",
  );
});

test("native latest placeholder: colors and VoiceOver label untouched", () => {
  assert.match(
    rightColumn,
    /Text\("Waiting for the first assessment…"\)[\s\S]{0,200}?\.foregroundStyle\(\.secondary\)/,
    "waiting text keeps its secondary color",
  );
  assert.match(
    rightColumn,
    /\.accessibilityLabel\("Waiting for the first assessment"\)/,
    "waiting row keeps its combined VoiceOver label",
  );
  assert.match(
    rightColumn,
    /Text\(message\)[\s\S]{0,200}?\.foregroundStyle\(\.red\)/,
    "error text keeps its red color",
  );
  assert.match(
    rightColumn,
    /Text\("No assessment received yet\."\)[\s\S]{0,200}?\.foregroundStyle\(\.secondary\)/,
    "no-assessment text keeps its secondary color",
  );
});
