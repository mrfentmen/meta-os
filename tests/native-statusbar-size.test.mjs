// Node built-in test runner, no dependencies:
//   node --test tests/native-statusbar-size.test.mjs
//
// IGNIS-UI-44 (Del UI push, Oct 29): native status-bar size parity.
// The web status lines are 13px or 12.5px mono — .status at 13px,
// #in-flight as .note at 13px, and #last-round-trip, #sampler-stats,
// and #log-stats as .note.mono at 12.5px — but the native StatusBar
// used .callout (16pt) for all five lines, so the whole bar read
// larger than every web line it mirrors while the footer below it
// (UI-23) already matched its own 13px web rule. The fix gives the
// backend message and the in-flight line 13pt, and the round-trip,
// sampler-stats, and log-entries lines 12.5pt monospaced, keeping
// the two-line limit, the muted colors, the wording, and the Export
// and Clear buttons. No Swift toolchain exists in this sandbox, so
// these are static checks on the shipped Swift.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const content = readFileSync(
  new URL("../native/Sources/MetaTrio/Views/ContentView.swift", import.meta.url),
  "utf8",
);

const barStart = content.indexOf("private struct StatusBar");
assert.ok(barStart >= 0, "StatusBar exists");
const bar = content.slice(barStart);
assert.ok(bar.length > 0, "StatusBar block exists");

function lineAfter(marker, length = 400) {
  const start = bar.indexOf(marker);
  assert.ok(start >= 0, `${marker} exists`);
  return bar.slice(start, start + length);
}

const backend = lineAfter("Text(model.backendStatus.message)");
const inFlight = lineAfter('Text("Assessment request in flight…")');
const roundTrip = lineAfter('Text("Last round trip:');
const ticks = lineAfter('Text("Ticks:');
const logCount = lineAfter('Text("Session log entries:');

test("native status bar: web contract — status 13px, note 13px, mono 12.5px", () => {
  const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
  assert.match(
    css,
    /\.status \{\s+margin: 0;\s+font-size: 13px;/,
    "web .status is 13px",
  );
  assert.match(
    css,
    /\.note \{\s+color: var\(--muted\);\s+font-size: 13px;\s+\}/,
    "web .note is 13px",
  );
  assert.match(
    css,
    /\.mono \{\s+font-family: var\(--mono\);\s+font-size: 12\.5px;\s+\}/,
    "web .mono is 12.5px",
  );
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.ok(
    html.includes('<p id="backend-status" class="status"'),
    "web backend status carries .status",
  );
  assert.ok(
    html.includes('<p id="in-flight" class="note"'),
    "web in-flight line carries .note",
  );
  assert.ok(
    html.includes('<p id="sampler-stats" class="note mono">') &&
      html.includes('<p id="last-round-trip" class="note mono"') &&
      html.includes('<p id="log-stats" class="note mono">'),
    "web round-trip, sampler-stats, and log-stats lines carry .note.mono",
  );
});

test("native status bar: backend and in-flight lines take 13pt, no callout left", () => {
  assert.match(backend, /\.font\(\.system\(size: 13\)\)/, "backend takes 13pt");
  assert.match(inFlight, /\.font\(\.system\(size: 13\)\)/, "in-flight takes 13pt");
  assert.doesNotMatch(backend, /\.font\(\.callout\)/, "no callout on backend");
  assert.doesNotMatch(inFlight, /\.font\(\.callout\)/, "no callout on in-flight");
});

test("native status bar: round-trip, ticks, and log lines take 12.5pt mono, no callout left", () => {
  for (const [name, block] of [
    ["round-trip", roundTrip],
    ["ticks", ticks],
    ["log-entries", logCount],
  ]) {
    assert.match(
      block,
      /\.font\(\.system\(size: 12\.5, design: \.monospaced\)\)/,
      `${name} takes 12.5pt monospaced`,
    );
    assert.doesNotMatch(block, /\.font\(\.callout\)/, `no callout on ${name}`);
  }
});

test("native status bar: keeps its limit, colors, wording, and buttons", () => {
  assert.match(backend, /\.lineLimit\(2\)/, "backend keeps its two-line limit");
  for (const block of [inFlight, roundTrip, ticks, logCount]) {
    assert.match(block, /\.foregroundStyle\(\.secondary\)/, "line keeps its muted color");
  }
  assert.ok(
    bar.includes('Button("Export Log")') && bar.includes('Button("Clear Log")'),
    "Export and Clear buttons stay",
  );
  assert.doesNotMatch(bar, /\.font\(\.callout\)/, "no callout left anywhere in the bar");
});
