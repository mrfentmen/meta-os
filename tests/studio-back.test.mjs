// Node built-in test runner, no dependencies:
//   node --test tests/studio-back.test.mjs
//
// HANA Agent1: STUDIO-BACK — the full logo studio page (the one
// the console Logo panel links to) used to be a dead end: once it
// opened, the only way back to the console was the browser's own
// Back button, because the studio header carried no link home.
// Now the studio header carries a Back to console link to the
// console page, styled in the studio's accent, sitting under the
// studio title so it fits narrow screens too. The shipped root
// studio (logo-studio.html) is untouched — it is the verbatim v2
// file, and this slice does not change it. These are static checks
// over the shipped source, the same pattern as the other logo
// tests; no live browser click is witnessed here.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const studio = readFileSync(
  new URL("../design/meta-ascii-logo-studio.html", import.meta.url),
  "utf8",
);
const rootStudio = readFileSync(
  new URL("../logo-studio.html", import.meta.url),
  "utf8",
);
const panel = readFileSync(new URL("../index.html", import.meta.url), "utf8");

test("studio header links back to the console", () => {
  assert.match(
    studio,
    /<a class="back-link" href="\.\.\/index\.html">← Back to console<\/a>/,
    "studio carries a Back to console link to ../index.html",
  );
  const link = studio.indexOf('class="back-link"');
  const headerEnd = studio.indexOf("</header>", link);
  assert.ok(
    link !== -1 && headerEnd !== -1 && headerEnd > link,
    "back link sits inside the studio header, under the title",
  );
  assert.match(
    panel,
    /<a class="logo-studio-link" href="design\/meta-ascii-logo-studio\.html">Open the full logo studio<\/a>/,
    "console Logo panel still links out to the full studio page",
  );
});

test("back link is styled in the studio accent", () => {
  assert.match(
    studio,
    /\.back-link \{[^}]*color: var\(--accent-light\);/s,
    "studio stylesheet colors .back-link in the accent light",
  );
  assert.match(
    studio,
    /\.back-link:hover,\s*\.back-link:focus-visible \{[^}]*text-decoration: underline;/s,
    "back link underlines on hover and keyboard focus",
  );
});

test("shipped root studio is untouched by this slice", () => {
  assert.ok(
    !rootStudio.includes("back-link"),
    "logo-studio.html carries no back link — the verbatim v2 file is unchanged",
  );
});
