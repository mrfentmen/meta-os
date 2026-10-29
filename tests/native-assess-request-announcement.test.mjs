// Node built-in test runner, no dependencies:
//   node --test tests/native-assess-request-announcement.test.mjs
//
// Native one-shot assess VoiceOver parity. The web frontend's
// backend-status line is a polite live region, so tapping "Assess this
// image" or "Assess this frame" reads its "Contacting model backend …"
// line aloud there; the native app used to set the same line silently,
// so a VoiceOver user who had just tapped Assess heard nothing at all
// until the result or the failure arrived, and a slow backend sounded
// exactly like a dead tap. Both tap paths now announce the line in its
// own words. Swift cannot run in this sandbox, so the announcement is
// asserted from source, in the same style as the other native tests.

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
const webApp = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");

const stillImageRun = model.slice(
  model.indexOf("func runStillImageAssessment("),
  model.indexOf("func clearStillImage()"),
);
const videoRun = model.slice(
  model.indexOf("func runVideoFrameAssessment("),
  model.indexOf("func clearVideo()"),
);
const sampler = model.slice(
  model.indexOf("private func runSample()"),
  model.indexOf("private func submitAssessment("),
);
const submit = model.slice(
  model.indexOf("private func submitAssessment("),
  model.indexOf("private func recordLog("),
);
const startAnalysis = model.slice(
  model.indexOf("func startAnalysis()"),
  model.indexOf("func stopAnalysis()"),
);

test("anchor: the web backend-status line is a polite live region, so its Contacting line is heard", () => {
  assert.match(
    html,
    /id="backend-status"[^>]*aria-live="polite"/,
  );
  assert.match(webApp, /setBackendStatus\("unknown", `Contacting model backend:/);
});

test("service: a request-started announcement posts the message verbatim, unprefixed", () => {
  assert.match(
    announcements,
    /static func requestStarted\(_ message: String\) \{\s*post\(message\)\s*\}/,
  );
  assert.doesNotMatch(
    announcements,
    /static func requestStarted[\s\S]*?Model backend not connected/,
  );
  assert.doesNotMatch(
    announcements,
    /static func requestStarted[\s\S]*?Frame capture failed/,
  );
});

test("still-image tap: the Contacting line is announced, after the generation guard", () => {
  const guardAt = stillImageRun.indexOf("guard generation == viewGeneration else { return }");
  assert.notEqual(guardAt, -1, "runStillImageAssessment is missing its generation guard");
  const announceAt = stillImageRun.indexOf(
    'AccessibilityAnnouncement.requestStarted("Contacting model backend: \\(trimmedEndpoint) …")',
  );
  assert.notEqual(announceAt, -1, "still-image run never announces the request start");
  assert.ok(announceAt > guardAt, "a stale tap must not announce");
  assert.match(
    stillImageRun,
    /backendStatus = \.unknown\("Contacting model backend: \\\(trimmedEndpoint\) …"\)/,
  );
});

test("video-frame tap: the Contacting line is announced, after the generation guard", () => {
  const guardAt = videoRun.indexOf("guard generation == viewGeneration else { return }");
  assert.notEqual(guardAt, -1, "runVideoFrameAssessment is missing its generation guard");
  const announceAt = videoRun.indexOf(
    'AccessibilityAnnouncement.requestStarted("Contacting model backend: \\(trimmedEndpoint) …")',
  );
  assert.notEqual(announceAt, -1, "video-frame run never announces the request start");
  assert.ok(announceAt > guardAt, "a stale tap must not announce");
  assert.match(
    videoRun,
    /backendStatus = \.unknown\("Contacting model backend: \\\(trimmedEndpoint\) …"\)/,
  );
});

test("no per-tick spam: the sampler and submit paths never announce a request start", () => {
  assert.doesNotMatch(sampler, /requestStarted/);
  assert.doesNotMatch(submit, /requestStarted/);
});

test("no double announcement: Start Analysis still announces only its banner, not a request start", () => {
  assert.doesNotMatch(startAnalysis, /requestStarted/);
  assert.match(startAnalysis, /AccessibilityAnnouncement\.analysisStarted\(/);
});
