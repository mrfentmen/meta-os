// Node built-in test runner, no dependencies:
//   node --test tests/ui-spark-status.test.mjs
//
// HANA Agent1: UI-SPARK-STATUS — UI_README's "What is NOT
// connected yet" bullet still said live model calls were held
// per Del's ruling, stale since Del's 2026-10-30 00:23 EDT
// green light via Pax put the Spark test phase LIVE ($75 test
// budget, key on the Mac only). The hardware doc gained that
// update in HARDWARE-LOGO, but the UI doc — the Agent 1
// deliverable a reader meets first — kept telling readers
// every request ends in the held error. Now the bullet keeps
// the 2026-10-28 held state as verified history, carries the
// test-phase update, and still says plainly what is unproven:
// a live assessment driven from the web or native UI, with no
// live calls from this sandbox. Docs only, no code change,
// no Swift change, no live calls.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const readme = readFileSync(
  new URL("../UI_README.md", import.meta.url),
  "utf8",
);
const hardware = readFileSync(
  new URL("../docs/HARDWARE_VERIFICATION.md", import.meta.url),
  "utf8",
);

test("ui spark status: the test phase is live, not held", () => {
  assert.ok(
    readme.includes("the Spark test phase is LIVE"),
    "UI_README must say the Spark test phase is live",
  );
  assert.ok(
    readme.includes("2026-10-30 00:23 EDT"),
    "UI_README must date the green light",
  );
  assert.ok(
    readme.includes("$75 test budget"),
    "UI_README must carry the test budget",
  );
  assert.ok(
    !readme.includes("live model calls are held per Del's ruling"),
    "the old held-as-current claim must be gone",
  );
  assert.ok(
    !readme.includes("Until live calls are enabled, every analysis request ends"),
    "the old until-enabled claim must be gone",
  );
});

test("ui spark status: held state kept as history, key kept off the bus", () => {
  assert.ok(
    readme.includes("live_enabled: false"),
    "the 2026-10-28 held-state verification stays as history",
  );
  assert.match(
    readme,
    /never on the\s+bus, never committed/,
    "the key rule stays: on the Mac only, never on the bus, never committed",
  );
  assert.ok(
    !/SPARK_API_KEY\s*=\s*\S/.test(readme),
    "UI_README must not carry a key value",
  );
});

test("ui spark status: what is still unproven stays unproven", () => {
  assert.ok(
    readme.includes("still unproven"),
    "the UI-driven live round trip must still read unproven",
  );
  assert.ok(
    readme.includes("this sandbox still makes no live calls"),
    "the sandbox must still make no live calls",
  );
});

test("ui spark status: UI doc agrees with the hardware doc", () => {
  assert.ok(
    hardware.includes("Spark test phase LIVE since 2026-10-30"),
    "the hardware doc still carries the test-phase status",
  );
  assert.ok(
    readme.includes("docs/HARDWARE_VERIFICATION.md"),
    "UI_README must point at the hardware doc for the same status",
  );
});
