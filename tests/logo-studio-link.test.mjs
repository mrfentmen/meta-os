// Node built-in test runner, no dependencies:
//   node --test tests/logo-studio-link.test.mjs
//
// HANA Agent1: the uploaded Meta ASCII logo studio is part of the
// app now, not a loose file. The main page links to it from the
// header, the link carries the studio link class, the stylesheet
// styles that class, and the shipped studio file is the uploaded
// v2 file with its Meta Symbol title intact.
// HANA Agent1: HEADER-STUDIO — the header link used to point at
// the root v2 viewer (logo-studio.html), while the Logo panel
// links to the full studio (design/meta-ascii-logo-studio.html),
// so the console offered two different "studio" pages and the
// header one had no color controls, no saved choices, and no way
// back. Now both console links land on the same full studio, and
// the root v2 file stays on disk untouched as the shipped
// artifact its own guards describe.

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
    /<a class="logo-studio-link" href="design\/meta-ascii-logo-studio\.html">Logo studio<\/a>/,
    "index.html header carries a Logo studio link to design/meta-ascii-logo-studio.html",
  );
});

test("header and Logo panel links land on the same studio", () => {
  const header = html.match(
    /<a class="logo-studio-link" href="([^"]+)">Logo studio<\/a>/,
  );
  const panel = html.match(
    /<a class="logo-studio-link" href="([^"]+)">Open the full logo studio<\/a>/,
  );
  assert.ok(header, "header Logo studio link exists");
  assert.ok(panel, "Logo panel full-studio link exists");
  assert.equal(
    header[1],
    panel[1],
    "header and panel studio links point at the same page",
  );
  assert.equal(
    header[1],
    "design/meta-ascii-logo-studio.html",
    "both links point at the full studio, not the root v2 viewer",
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
