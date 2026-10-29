// Node built-in test runner, no dependencies:
//   node --test tests/native-export-failure-announcement.test.mjs
//
// Native session-log export failure VoiceOver parity. Every other
// error the native app puts in its status bar is announced to
// VoiceOver — a backend failure through backendFailure, a capture
// failure verbatim through captureFailure, a settled health result
// through healthResult — but the export failure was not: exportLog's
// catch set backendStatus to "Session log export failed: …" and said
// nothing, so a VoiceOver user never heard that the export they had
// just asked for had failed. The status bar is not a live region, so
// the on-screen text alone does not reach them. The failure is now
// announced in the status line's own words, through its own function:
// it is not a backend failure — the export writes a file and sends
// nothing to the backend, and the backend may be perfectly fine — so
// routing it through backendFailure would mislead. Swift cannot run
// in this sandbox, so the announcement is asserted from source, in
// the same style as the other native tests. The web frontend needs
// no change: its export is a browser download with no failure surface
// that sets a status line.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const announcements = readFileSync(
  new URL("../native/Sources/MetaTrio/Services/AccessibilityAnnouncement.swift", import.meta.url),
  "utf8",
);
const model = readFileSync(
  new URL("../native/Sources/MetaTrio/ViewModels/AppModel.swift", import.meta.url),
  "utf8",
);

const exportLog = model.slice(
  model.indexOf("func exportLog()"),
  model.indexOf("// MARK: - Sampling pipeline"),
);

test("service: an export-failure announcement posts the message verbatim, unprefixed", () => {
  assert.match(
    announcements,
    /static func exportFailure\(_ message: String\) \{\s*post\(message\)\s*\}/,
  );
  assert.doesNotMatch(
    announcements,
    /static func exportFailure[\s\S]*?Model backend not connected/,
  );
});

test("native: the export failure is announced in the status line's own words", () => {
  assert.match(
    exportLog,
    /let message = "Session log export failed: \\\(error\.localizedDescription\)"\s*backendStatus = \.error\(message\)\s*AccessibilityAnnouncement\.exportFailure\(message\)/,
  );
});

test("native: the announcement appears exactly once, in the export catch — never as a backend failure", () => {
  const calls = exportLog.match(/exportFailure\(message\)/g) ?? [];
  assert.equal(calls.length, 1);
  assert.doesNotMatch(exportLog, /backendFailure/);
});

test("native: no other error status in AppModel is left silent", () => {
  // Every .error assignment in the model must sit next to an
  // announcement call: the two capture failures through
  // captureFailure, the submit failure through backendFailure, and
  // the export failure through exportFailure. The .unknown and
  // .connected assignments are interim or covered by the assessment
  // announcement, so only .error is audited here.
  const errorLines = model
    .split("\n")
    .map((line, i) => [line, i])
    .filter(([line]) => /backendStatus = \.error\(/.test(line));
  assert.ok(errorLines.length >= 4, "expected the known .error assignments to audit");
  for (const [line, i] of errorLines) {
    // The announcement need not sit on the next line: the capture
    // paths explain themselves in comments first, so allow the
    // comment block between the status and its announcement.
    const window = model.split("\n").slice(i, i + 20).join("\n");
    assert.match(
      window,
      /AccessibilityAnnouncement\.(captureFailure|backendFailure|exportFailure)\(/,
      `unannounced error status: ${line.trim()}`,
    );
  }
});
