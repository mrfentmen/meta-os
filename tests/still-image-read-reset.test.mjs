// Node built-in test runner, no dependencies:
//   node --test tests/still-image-read-reset.test.mjs
//
// Web still-image read vs Reset/Clear/second-choice parity. Choosing a
// file on the web reads it asynchronously (FileReader, then a decode
// probe), so a Reset, a Clear, or a second file choice could land while
// a read was still in flight — and the settling read then repainted
// the panel Reset had just cleared (preview, "Image ready" text, an
// enabled Assess button for a pre-reset image), or overwrote a newer
// file's "Reading image…" state with the earlier file. The read now
// captures a generation number when it starts; Clear bumps it, each
// new choice bumps it, and the read touches nothing once its number is
// stale, after every await and in its catch. The native picker reads
// synchronously, so it has no such window and needs no guard.
// This test reads the sources (it cannot run Swift in this sandbox,
// and app.js needs a DOM) to assert the guards are in place.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const model = readFileSync(
  new URL("../native/Sources/MetaTrio/ViewModels/AppModel.swift", import.meta.url),
  "utf8",
);
const web = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");

const webRead = web.slice(
  web.indexOf('els.imageInput.addEventListener("change"'),
  web.indexOf("els.btnImageAssess.addEventListener"),
);
const webClear = web.slice(
  web.indexOf("function clearStillImageInput()"),
  web.indexOf("els.btnImageClear.addEventListener"),
);
const webReset = web.slice(
  web.indexOf("els.btnReset.addEventListener"),
  web.indexOf("els.intervalSeconds.addEventListener"),
);
const nativeChoose = model.slice(
  model.indexOf("func chooseStillImage()"),
  model.indexOf("func assessStillImage()"),
);

test("anchor: Reset and Clear both go through clearStillImageInput, so a stale repaint would be visible", () => {
  assert.match(webReset, /clearStillImageInput\(\);/);
  assert.match(webClear, /els\.imagePreview\.hidden = true;/);
  assert.match(webClear, /els\.imageState\.textContent = "No image chosen\.";/);
  assert.match(webClear, /els\.btnImageAssess\.disabled = true;/);
});

test("web: each choice captures a read generation, bumped before any await", () => {
  assert.match(webRead, /const readGeneration = \+\+stillImageReadGeneration;/);
});

test("web: Clear bumps the read generation, invalidating a read in flight", () => {
  assert.match(webClear, /stillImageReadGeneration \+= 1;/);
});

test("web: the read checks its generation after every await and in its catch", () => {
  const guards = webRead.match(
    /if \(readGeneration !== stillImageReadGeneration\) return;/g,
  );
  assert.ok(
    guards && guards.length >= 3,
    `expected a staleness guard after the file read, after the decode probe, and in the catch; found ${guards ? guards.length : 0}`,
  );
});

test("native: the still-image read has no suspension point, so no guard is needed", () => {
  assert.doesNotMatch(nativeChoose, /\bawait\b/);
  assert.doesNotMatch(nativeChoose, /Task\s*\{/);
});
