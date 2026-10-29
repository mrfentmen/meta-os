// Node built-in test runner, no dependencies:
//   node --test tests/latest-uncertainty-empty-note.test.mjs
//
// HANA Agent1: the Latest panel's empty uncertainty note reads at body
// size, like the native panel's note. The native empty note is now an
// explicit 15pt Text, secondary (see the uncertainty-size test: the
// native default read smaller than the web's 15px body size, as UI-20
// showed for the summary) — and the web's own populated uncertainty
// items read at body size in --muted, but the web empty note used class
// "note" (13px), so an assessment with no uncertainty items read its
// note smaller than both its own populated list and the native note.
// The note now carries class "uncertainty" — muted color, body size
// inherited — changing no wording, no heading, and no populated-list
// rendering. No Swift toolchain exists in this sandbox, so the native
// side is checked statically on the shipped Swift.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
const swift = readFileSync(
  new URL(
    "../native/Sources/MetaTrio/Views/AssessmentView.swift",
    import.meta.url,
  ),
  "utf8",
);

test("web empty uncertainty note: <p> with class uncertainty, not note", () => {
  assert.match(
    app,
    /const uncertainty = document\.createElement\("p"\);\s+uncertainty\.className = "uncertainty";\s+uncertainty\.textContent = "The model reported no uncertainty items\.";/,
    "empty branch renders a <p> with class uncertainty and the same wording",
  );
});

test("web .uncertainty rule: muted color, no font-size, so body size is inherited", () => {
  const rule = css.match(/\.uncertainty \{[^}]*\}/);
  assert.ok(rule, ".uncertainty rule exists");
  assert.match(rule[0], /color: var\(--muted\);/, "uncertainty items stay muted");
  assert.doesNotMatch(rule[0], /font-size/, "no font-size override in the rule");
  assert.match(css, /body \{[^}]*font-size: 15px;/, "body size is 15px to inherit");
});

test("native empty uncertainty note: secondary, explicit 15pt font", () => {
  // Superseded guard, not dropped: this test once asserted the note
  // carried no explicit font, because the native default was taken as
  // body size. UI-20 showed the default reads smaller than the web's
  // 15px body size, so the note now carries an explicit 15pt font,
  // governed by tests/native-ignis-assessment-uncertainty-size.test.mjs.
  // This guard keeps the secondary color and the explicit size here.
  const start = swift.indexOf('Text("The model reported no uncertainty items.")');
  assert.ok(start >= 0, "native empty note exists");
  const note = swift.slice(start, swift.indexOf("} else {", start));
  assert.match(note, /\.foregroundStyle\(\.secondary\)/, "note stays secondary");
  assert.match(note, /\.font\(\.system\(size: 15\)\)/, "note carries the 15pt font");
});

test("guards: populated list and earlier note unchanged", () => {
  assert.match(
    app,
    /const uncertainty = document\.createElement\("ul"\);\s+uncertainty\.className = "uncertainty";/,
    "populated branch still renders a <ul> with class uncertainty",
  );
  assert.match(
    app,
    /const note = document\.createElement\("p"\);\s+note\.className = "note";/,
    "earlierNote paragraph above the panel still uses class note",
  );
});
