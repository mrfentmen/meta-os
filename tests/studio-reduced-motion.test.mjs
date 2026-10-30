// Node built-in test runner, no dependencies:
//   node --test tests/studio-reduced-motion.test.mjs
//
// HANA Agent1: STUDIO-REDUCED-MOTION — the console's loop
// behind the panels renders one still frame under Reduce
// Motion (js/logo-background.js gates its advance and its
// animation loop on reducedMotion), but the full logo studio
// kept spinning: its CSS only killed transitions, while
// renderFrame kept looping and advancing the angles. So a
// Reduce Motion user who opened the studio still got a
// spinning logo, even though the console's own check 7 in
// the hardware doc promises one still frame. Now the studio
// matches the console: under Reduce Motion it renders one
// still frame and stops the loop, and repaints that one
// frame only when the user changes something by hand (a
// drag, an arrow key, a color, a resize), so a color choice
// still shows up without the loop ever restarting. The
// shipped root studio (logo-studio.html) is untouched —
// it is the verbatim v2 file, and this slice does not
// change it. These are static checks over the shipped
// source, the same pattern as the other logo tests; no
// live browser click is witnessed here.

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

test("studio detects Reduce Motion the console's way", () => {
  assert.match(
    studio,
    /const reducedMotion =\s*\n?\s*typeof window\.matchMedia === "function" &&\s*\n?\s*window\.matchMedia\("\(prefers-reduced-motion: reduce\)"\)\.matches;/,
    "studio defines reducedMotion from matchMedia, guarded like the console background",
  );
});

test("studio does not advance or loop under Reduce Motion", () => {
  assert.match(
    studio,
    /if \(!isDragging && !isPaused && !reducedMotion\) \{/,
    "auto-advance is gated on not being reduced motion",
  );
  assert.match(
    studio,
    /if \(!reducedMotion\) requestAnimationFrame\(renderFrame\);/,
    "the loop does not reschedule itself under Reduce Motion",
  );
  assert.doesNotMatch(
    studio,
    /^\s*requestAnimationFrame\(renderFrame\);$/m,
    "no unconditional animation-frame scheduling remains in the studio",
  );
  const frame = studio.slice(studio.indexOf("function renderFrame"));
  assert.match(
    frame,
    /if \(!reducedMotion\) requestAnimationFrame\(renderFrame\);/,
    "the early no-size return also stops instead of looping under Reduce Motion",
  );
});

test("studio repaints its one still frame on hand changes only", () => {
  const drag = studio.slice(studio.indexOf("addEventListener('pointermove'"));
  assert.match(
    drag,
    /if \(reducedMotion\) renderFrame\(\);/,
    "a drag repaints the still frame at the dragged angles",
  );
  const keys = studio.slice(studio.indexOf("addEventListener('keydown'"));
  assert.match(
    keys,
    /if \(reducedMotion\) renderFrame\(\);/,
    "an arrow-key turn repaints the still frame",
  );
  const color = studio.slice(
    studio.indexOf("function setAccentColor"),
    studio.indexOf("colorPicker.addEventListener"),
  );
  assert.match(
    color,
    /if \(reducedMotion\) renderFrame\(\);/,
    "a color change repaints the re-tinted still frame",
  );
  assert.match(
    studio,
    /new ResizeObserver\(\(\) => \{\s*\n?\s*resizeCanvas\(\);\s*\n?\s*if \(reducedMotion\) renderFrame\(\);/,
    "a resize repaints the still frame instead of leaving a cleared canvas",
  );
});

test("studio defaults and shipped root studio are unchanged", () => {
  assert.match(
    studio,
    /const DEFAULT_ACCENT = '#1877f2';/,
    "studio default color is still Meta blue",
  );
  assert.ok(
    !rootStudio.includes("reducedMotion"),
    "logo-studio.html carries no reducedMotion handling — the verbatim v2 file is unchanged",
  );
});
