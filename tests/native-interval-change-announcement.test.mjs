// Node built-in test runner, no dependencies:
//   node --test tests/native-interval-change-announcement.test.mjs
//
// Web <-> native mid-run interval-change announcement parity. The
// camera panel's ANALYSIS ACTIVE banner is the confirmation that
// sampling is running and at what interval, and it is reworded when
// the interval changes mid-run — but it used to be reworded silently
// on native. On the web the interval change handler rewords the
// banner through updateAnalysisActive, and the banner is a polite,
// atomic live region, so a VoiceOver user who changed the interval
// mid-run heard the new interval there; while idle the banner is
// hidden, so an idle change reads nothing. On native the Stepper
// binds intervalSeconds, and its didSet only moved the sampler
// interval: the banner's SwiftUI label reworded, but a label change
// posts no announcement, so a VoiceOver user who stepped the
// interval mid-run heard the Stepper's new number and nothing
// confirming sampling was still active at that interval. The didSet
// now posts the banner's own words, through the same helper as the
// start announcement, guarded on a run actually being active: an
// idle change stays silent, since the banner is hidden and the next
// Start announces the interval then. An interval change sends no
// frame, so it is never announced as a backend or capture failure,
// and it is a user action, never a sampler tick, so unlike the
// sampler-stats line there is no per-second spam risk. This test
// reads the Swift sources (it cannot run Swift in this sandbox) to
// assert the announcement exists, is guarded on a live run, and
// matches the banner's own words.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const page = readFileSync(new URL("../index.html", import.meta.url), "utf8");
const web = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
const model = readFileSync(
  new URL(
    "../native/Sources/MetaTrio/ViewModels/AppModel.swift",
    import.meta.url,
  ),
  "utf8",
);
const contentView = readFileSync(
  new URL("../native/Sources/MetaTrio/Views/ContentView.swift", import.meta.url),
  "utf8",
);

const analysisTag = page.match(/<p id="analysis-active"[^>]*>/);
assert.ok(analysisTag, "index.html is missing its analysis-active element");

const didSet = model.slice(
  model.indexOf("@Published var intervalSeconds"),
  model.indexOf("@Published var scenarioLabel"),
);
const intervalHandler = web.slice(
  web.indexOf('els.intervalSeconds.addEventListener("change"'),
  web.indexOf('els.btnClearLog.addEventListener("click"'),
);

test("web: the interval change handler rewords the banner", () => {
  assert.ok(
    intervalHandler.includes("updateAnalysisActive()"),
    "interval change handler no longer rewords the banner",
  );
});

test("web: the banner is a polite, atomic live region, so a mid-run rewording is read aloud", () => {
  assert.match(analysisTag[0], /aria-live="polite"/);
  assert.match(analysisTag[0], /aria-atomic="true"/);
});

test("native: a mid-run interval change announces the banner's own words", () => {
  assert.ok(
    contentView.includes(
      'accessibilityLabel("Analysis active, sampling one frame every \\(model.intervalSeconds) seconds")',
    ),
    "native banner label changed — the announcement must match it",
  );
  assert.match(
    didSet,
    /if analysisRunning \{\s*AccessibilityAnnouncement\.analysisStarted\("Analysis active, sampling one frame every \\\(intervalSeconds\) seconds"\)/,
  );
});

test("native: an idle interval change stays silent (the banner is hidden, the next Start announces)", () => {
  const calls = didSet.match(/AccessibilityAnnouncement\.analysisStarted/g) ?? [];
  assert.equal(
    calls.length,
    1,
    "intervalSeconds didSet must hold exactly one announcement call, guarded on a live run",
  );
  assert.ok(
    didSet.includes("if analysisRunning"),
    "intervalSeconds didSet no longer guards its announcement on a live run",
  );
});

test("native: the interval change is not announced as a backend or capture failure", () => {
  assert.doesNotMatch(didSet, /backendFailure|captureFailure/);
});
