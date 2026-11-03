// Node built-in test runner, no dependencies:  node --test tests/ui-wave-empty-states.test.mjs
// Covers HN-012 (designed empty states): every audit panel's empty
// state says what the panel is, why it is empty, and what fills it.
// Two panels are pinned exceptions, not oversights: the event
// history and latest-assessment sentences are pinned by native
// parity tests in tests/ui.test.mjs (the native timeline / latest
// panel carry the same sentences), so their copy stays exactly as
// pinned and this test guards that pin instead of rewriting them.

import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const html = readFileSync(new URL("../imperium/index.html", import.meta.url), "utf8");
const mapJs = readFileSync(new URL("../js/command-map.js", import.meta.url), "utf8");
const appJs = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");

test("incident queue empty state says what it is and what fills it", () => {
  assert.match(html, /id="cmd-alerts-empty"[^>]*>No cameras flagged yet\. This queue holds flags from all three divisions\. It fills when a watched camera's assessment flags it for human review\./);
});

test("inspector empty state names the action that fills it", () => {
  assert.match(html, /id="cmd-insp-meta"[^>]*>Choose a camera from the list or the map\. The inspector shows its live snapshot, status, and latest assessment here\./);
});

test("loop feed empty state says what fills it", () => {
  assert.match(mapJs, /No crew events recorded yet\. This feed shows the agent crew's patrol, review, investigation, and response activity\. It fills once the crew has run on this stack\./);
});

test("camera wall empty state says what fills it", () => {
  assert.match(mapJs, /No watched cameras yet\. This wall shows watched cameras' live snapshots\. Select a camera and choose Watch to fill it\./);
});

test("camera list empty state tells the operator to clear the filter", () => {
  assert.match(mapJs, /No cameras match the filter\. Clear the filter to see the full loaded list again\./);
});

test("session log empty note exists and hides once entries exist", () => {
  assert.ok(html.includes('<p id="log-empty" class="note empty-state">No session entries yet. This log fills as frames are assessed or requests fail.</p>'));
  assert.ok(appJs.includes('logEmpty: $("log-empty")'));
  assert.match(appJs, /els\.logEmpty\.hidden = log\.count > 0;/);
});

test("empty states share one visual marker", () => {
  assert.ok(css.includes(".empty-state { border-left: 2px solid var(--panel-border); padding-left: 8px; }"));
});

test("pinned exceptions: history and latest keep their parity sentences", () => {
  assert.match(html, /id="history-empty"[^>]*>No events yet\. Assessments and errors will appear here\./);
  assert.match(html, /id="latest-assessment"[^>]*>No assessment received yet\./);
});
