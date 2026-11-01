// Node built-in test runner, no dependencies:  node --test tests/ui-wave-timezone.test.mjs
// Covers HN-024 (timezone honesty): every timestamp renders in
// the viewer's timezone with the zone named. Deterministic checks
// pass an explicit timeZone; the shipped code passes none, so it
// uses the viewer's own zone. The old console clock's literal
// " LOCAL" is gone — a label that named no zone at all.

import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { formatTimeWithZone, zoneName } from "../js/timefmt.js";

const mapJs = readFileSync(new URL("../js/command-map.js", import.meta.url), "utf8");
const clockJs = readFileSync(new URL("../js/console-clock.js", import.meta.url), "utf8");

test("winter and summer times name their zone", () => {
  // 2026-01-15 13:00 UTC = 08:00 EST; 2026-07-15 13:00 UTC = 09:00 EDT.
  assert.match(formatTimeWithZone("2026-01-15T13:00:00.000Z", { timeZone: "America/New_York" }), /08:00:00 EST/);
  assert.match(formatTimeWithZone("2026-07-15T13:00:00.000Z", { timeZone: "America/New_York" }), /09:00:00 EDT/);
  assert.equal(zoneName({ timeZone: "UTC" }), "UTC");
});

test("bad input passes through, never a fabricated time", () => {
  assert.equal(formatTimeWithZone("not a date"), "not a date");
  assert.equal(formatTimeWithZone(""), "");
});

test("fmtTime delegates, so every call site inherits the zone name", () => {
  assert.ok(mapJs.includes('import { formatTimeWithZone } from "./timefmt.js";'));
  assert.match(mapJs, /function fmtTime\(value\) \{\n\s+\/\/ HN-024: delegates to timefmt[\s\S]*?\n\s+return formatTimeWithZone\(value\);\n\}/);
  assert.ok(!mapJs.includes("toLocaleTimeString"));
});

test("console clock names the real zone, not the literal LOCAL", () => {
  assert.ok(!/\+ " LOCAL"/.test(clockJs), "clock must not append the literal LOCAL");
  assert.ok(clockJs.includes('timeZoneName: "short"'));
  assert.ok(clockJs.includes('parts[i].type === "timeZoneName"'));
});
