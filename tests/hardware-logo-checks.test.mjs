// Node built-in test runner, no dependencies:
//   node --test tests/hardware-logo-checks.test.mjs
//
// HANA Agent1 (Del direction, Oct 30): the Agent 1 hardware doc
// gains the Logo panel checks and a current Spark status. Until
// now the doc had no Logo checks at all — the panel (web LOGO-1 /
// LOGO-2, native LOGO-NATIVE-1..6) shipped with unit tests and
// inspection only — and its live-backend section still said live
// calls were held, which stopped being true when Del green-lit the
// Spark test phase 2026-10-30 00:23 EDT via Pax ($75 budget, key
// on the Mac only). Static checks on the doc only: nothing here
// claims a check was run on real hardware, and the held-state
// record from 2026-10-28 stays as history, not rewritten.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const doc = readFileSync(
  new URL("../docs/HARDWARE_VERIFICATION.md", import.meta.url),
  "utf8",
);

test("hardware doc: a Logo panel section exists, needing no camera", () => {
  assert.ok(doc.includes("## 5. Logo panel"), "Logo section must exist");
  assert.ok(
    doc.includes("no camera needed"),
    "Logo section must say it needs no camera",
  );
});

test("hardware doc: web Logo checks cover presets, picker, reset, speed, pause, persistence", () => {
  for (const phrase of [
    "Meta blue, Cyan",
    "Custom picker",
    "Reset to product color",
    "0% — the loop stands still",
    "100% — the loop runs clearly faster than at 25%",
    "Pause logo — the loop holds its last frame",
    "Resume",
    "reload the page",
  ]) {
    assert.ok(doc.includes(phrase), `web Logo checks must include: ${phrase}`);
  }
});

test("hardware doc: native Logo checks cover relaunch, hover, VoiceOver, reduced motion", () => {
  for (const phrase of [
    "Quit and relaunch the app",
    "Hover a swatch",
    "VoiceOver",
    "Paused or Playing",
    "Reduce Motion on, the loop renders one still",
  ]) {
    assert.ok(
      doc.includes(phrase),
      `native Logo checks must include: ${phrase}`,
    );
  }
  assert.ok(
    doc.includes("large logo stays in the web\n   studio"),
    "native checks must say the large logo stays in the web studio",
  );
});

test("hardware doc: live section names the test phase and keeps the UI round trip unproven", () => {
  assert.ok(doc.includes("test phase is LIVE"), "must name the live test phase");
  assert.ok(doc.includes("$75"), "must name the $75 test budget");
  assert.ok(
    doc.includes("never on the bus"),
    "must say the key is never on the bus",
  );
  assert.ok(
    doc.includes("What is still\nunproven is a live assessment driven from the web console"),
    "must keep the UI-driven live round trip unproven",
  );
  assert.ok(
    doc.includes("sandbox still makes\nno live calls"),
    "must say the sandbox still makes no live calls",
  );
});

test("hardware doc: held-state history kept, blocked claim gone, rest untouched", () => {
  assert.ok(
    doc.includes("2026-10-28") && doc.includes("live_enabled: false"),
    "2026-10-28 held-state record must stay as history",
  );
  assert.ok(
    !doc.includes("BLOCKED on live calls"),
    "the stale blocked-on-live-calls claim must be gone",
  );
  assert.ok(
    doc.includes("Never point a camera at a real fire"),
    "ground rules must be untouched",
  );
  assert.ok(
    doc.includes("Web on phone: NOT RUN"),
    "results log must keep the web-on-phone status",
  );
  assert.ok(
    doc.includes("Logo panel (web and native): NOT RUN on real hardware"),
    "results log must add the Logo panel as not run",
  );
});
