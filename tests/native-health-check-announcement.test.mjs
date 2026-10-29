// Node built-in test runner, no dependencies:
//   node --test tests/native-health-check-announcement.test.mjs
//
// Native health-check VoiceOver parity. The web frontend's health line
// is a polite live region, so a VoiceOver user hears a settled health
// result there; the native app used to set the same line silently, so
// the result never reached a VoiceOver user at all. The settled
// result — success or failure — is now announced in the health line's
// own words. The interim "Checking …" text is deliberately not
// announced, and a result from before a Reset Session must never be
// announced as current, so the announcement lives inside the same
// view-generation guard that applies the text. Swift cannot run in
// this sandbox, so the announcement is asserted from source, in the
// same style as the other native tests.

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
const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");

const nativeHealth = model.slice(
  model.indexOf("func checkBackendHealth()"),
  model.indexOf("// MARK: - Still-image input"),
);

test("anchor: the web health line is a polite live region, so its results are heard", () => {
  assert.match(
    html,
    /id="backend-health"[^>]*aria-live="polite"/,
  );
});

test("service: a health-result announcement posts the message verbatim, unprefixed", () => {
  assert.match(
    announcements,
    /static func healthResult\(_ message: String\) \{\s*post\(message\)\s*\}/,
  );
  assert.doesNotMatch(
    announcements,
    /static func healthResult[\s\S]*?Model backend not connected/,
  );
});

test("native: the settled health result is announced inside the view-generation guard", () => {
  assert.match(
    nativeHealth,
    /if requestGeneration == viewGeneration \{\s*backendHealth = resultText\s*AccessibilityAnnouncement\.healthResult\(resultText\)\s*\}/,
  );
});

test("native: the announcement appears exactly once, in the settle path — never on the interim text line", () => {
  const calls = nativeHealth.match(/healthResult\(resultText\)/g) ?? [];
  assert.equal(calls.length, 1);
  const checkingLine = nativeHealth
    .split("\n")
    .find((line) => line.includes('backendHealth = "Checking'));
  assert.ok(checkingLine, "interim Checking text is still set");
  assert.doesNotMatch(checkingLine, /healthResult/);
});
