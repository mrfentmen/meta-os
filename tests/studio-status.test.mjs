// Node built-in test runner, no dependencies:
//   node --test tests/studio-status.test.mjs
//
// HANA Agent1: STUDIO-STATUS — the full logo studio's top
// status read LIVE RENDER even under Reduce Motion, when the
// logo is one still frame, and a color change re-lit its glow
// dot the same way — so a Reduce Motion user was told the
// render was live while STUDIO-REDUCED-MOTION had stopped
// the loop. Now the status says STILL FRAME under Reduce
// Motion (paused still wins, then the still frame, then the
// live render), the still dot keeps its accent color but
// loses the glow, and the status is refreshed on load either
// way instead of only when a pause was saved. The shipped
// root studio (logo-studio.html) is untouched — it is the
// verbatim v2 file, and this slice does not change it.
// These are static checks over the shipped source, the same
// pattern as the other logo tests; no live browser click is
// witnessed here.

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

test("studio status: paused wins, then the still frame, then live", () => {
  const paused = studio.slice(studio.indexOf("function setPaused"));
  assert.match(
    paused,
    /statusLabel\.textContent = isPaused \? 'RENDER PAUSED' : \(reducedMotion \? 'STILL FRAME' : 'LIVE RENDER'\);/,
    "setPaused must label paused, then still, then live, in that order",
  );
});

test("studio status: the still dot keeps its color but loses its glow", () => {
  const paused = studio.slice(
    studio.indexOf("function setPaused"),
    studio.indexOf("speedSlider.addEventListener"),
  );
  assert.match(
    paused,
    /statusDot\.style\.boxShadow = \(isPaused \|\| reducedMotion\) \? 'none'/,
    "setPaused must kill the glow under Reduce Motion as well as when paused",
  );
  const color = studio.slice(
    studio.indexOf("function setAccentColor"),
    studio.indexOf("colorPicker.addEventListener"),
  );
  assert.match(
    color,
    /statusDot\.style\.boxShadow = \(isPaused \|\| reducedMotion\) \? 'none'/,
    "a color change must not re-light the glow over a still frame",
  );
  assert.ok(
    color.includes("statusDot.style.background = isPaused ? '#6f809d'"),
    "the still dot keeps its accent color; only paused turns it grey",
  );
});

test("studio status: the status is refreshed on load either way", () => {
  assert.ok(
    studio.includes("setPaused(storedPaused());"),
    "startup must run setPaused with the saved pause state, not only when paused",
  );
  assert.ok(
    !studio.includes("if (storedPaused()) setPaused(true);"),
    "the old paused-only startup call must be gone, or a Reduce Motion open keeps LIVE RENDER",
  );
});

test("studio status: live and paused labels and shipped root studio unchanged", () => {
  assert.ok(studio.includes("'LIVE RENDER'"), "the live label stays for a moving render");
  assert.ok(studio.includes("'RENDER PAUSED'"), "the paused label stays");
  assert.ok(studio.includes("const DEFAULT_ACCENT = '#1877f2';"), "studio default color unchanged");
  assert.ok(!rootStudio.includes("STILL FRAME"), "logo-studio.html carries no still-frame status — the verbatim v2 file is unchanged");
});
