// Node built-in test runner, no dependencies:  node --test tests/ui-wave-report.test.mjs
// Covers HN-025 (one-page UI fix report): the report exists,
// covers every wave task, and names what remains gated and why —
// it must not read as a shipping claim for work that still needs
// the boss's word.

import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const report = readFileSync(new URL("../docs/UI_FIX_REPORT.md", import.meta.url), "utf8");

test("report covers every wave task", () => {
  for (let n = 11; n <= 25; n++) {
    assert.ok(report.includes(`HN-0${n}`), `report must cover HN-0${n}`);
  }
});

test("report has all three sections", () => {
  assert.match(report, /## What was dead/);
  assert.match(report, /## What each fix does/);
  assert.match(report, /## What remains gated and why/);
});

test("report names every gated item and its reason", () => {
  for (const item of [
    "Merge to main",
    "HN-001…004, HN-008…010",
    "GOV-002",
    "viewer-posting",
    "Ignis gradient brand call",
    "Real-device 390 px check",
    "Screenshot captures",
    "Milo gate-1",
  ]) {
    assert.ok(report.includes(item), `report must name gated item: ${item}`);
  }
  assert.match(report, /needs the boss's word/);
  assert.match(report, /unmerged by design/);
});
