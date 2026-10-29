// Node built-in test runner, no dependencies:
//   node --test tests/logo-studio-link.test.mjs
//
// HANA Agent1: the uploaded Meta ASCII logo studio is part of the
// app now, not a loose file. The main page links to it from the
// header, the link carries the studio link class, the stylesheet
// styles that class, and the shipped studio file is the uploaded
// v2 file with its Meta Symbol title intact.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
const studio = readFileSync(
  new URL("../logo-studio.html", import.meta.url),
  "utf8",
);

test("header links to the logo studio page", () => {
  assert.match(
    html,
    /<a class="logo-studio-link" href="logo-studio\.html">Logo studio<\/a>/,
    "index.html header carries a Logo studio link to logo-studio.html",
  );
});

test("stylesheet styles the logo studio link", () => {
  assert.match(
    css,
    /\.logo-studio-link \{[^}]*color: var\(--accent\);/,
    "styles.css styles .logo-studio-link in the product accent color",
  );
});

test("shipped studio file is the uploaded v2 ASCII studio", () => {
  assert.match(
    studio,
    /<title>Meta Symbol \| ASCII Studio<\/title>/,
    "logo-studio.html keeps the uploaded v2 title",
  );
  assert.match(
    studio,
    /124 × 52 CHARACTER FIELD/,
    "logo-studio.html keeps the v2 character-field footer",
  );
});
