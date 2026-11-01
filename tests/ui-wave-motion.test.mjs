// Node built-in test runner, no dependencies:  node --test tests/ui-wave-motion.test.mjs
// Covers HN-017 (reduced motion): the ASCII logo spin already
// stops itself in js/logo-background.js (its frame loop and angle
// advance are gated on the media query) — this test pins that
// gating — and the camera wall's auto-cycling interval is now
// gated the same way at load, with CSS pulses stopped too.

import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

import { prefersReducedMotion } from "../js/motion.js";

const mapJs = readFileSync(new URL("../js/command-map.js", import.meta.url), "utf8");
const logoJs = readFileSync(new URL("../js/logo-background.js", import.meta.url), "utf8");
const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");

const yes = () => ({ matches: true });
const no = () => ({ matches: false });

test("prefersReducedMotion follows the media query, safely", () => {
  assert.equal(prefersReducedMotion(yes), true);
  assert.equal(prefersReducedMotion(no), false);
  assert.equal(prefersReducedMotion(null), false);
  assert.equal(prefersReducedMotion(() => { throw new Error("boom"); }), false);
});

test("wall auto-cycling is gated on the preference at load", () => {
  assert.ok(mapJs.includes('import { prefersReducedMotion } from "./motion.js";'));
  assert.match(mapJs, /if \(!prefersReducedMotion\(\)\) setInterval\(refreshWallSrcs, 15000\);/);
});

test("ASCII spin already stops itself under reduced motion", () => {
  assert.match(logoJs, /window\.matchMedia\("\(prefers-reduced-motion: reduce\)"\)\.matches/);
  assert.match(logoJs, /if \(!reducedMotion && !userPaused\) angleY \+= speedStep;/);
  assert.match(logoJs, /if \(running && !reducedMotion && !userPaused\) requestAnimationFrame\(renderFrame\);/);
});

test("CSS pulses and bar transitions stop under reduced motion", () => {
  const block = css.slice(css.indexOf("@media (prefers-reduced-motion: reduce)"));
  assert.ok(block.length > 0);
  assert.match(block, /\.cmd-pin--fast, \.cmd-pin--slow, \.cmd-step--current \.cmd-step-dot \{ animation: none; \}/);
  assert.match(block, /\.cmd-bar span \{ transition: none; \}/);
});
