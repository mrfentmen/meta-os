// Node built-in test runner, no dependencies:
//   node --test tests/analysis-active-announcement.test.mjs
//
// Web <-> native analysis-start announcement parity. The camera panel's
// ANALYSIS ACTIVE banner is the confirmation that sampling is running
// and at what interval — the sampler counters move every tick, but a
// counter is not a confirmation — and it used to appear silently on
// both frontends. On the web a Start tap also moves the backend-status
// line to "Contacting model backend", which says a request path is
// opening, but never confirms sampling is running or at what interval;
// on native even that line changes silently, so a VoiceOver user who
// had just tapped Start Analysis heard nothing at all. The web banner
// is now a polite, atomic live region, and the native start posts the
// banner's own words verbatim through a helper of its own: starting
// analysis sends no frame yet, so neither backendFailure nor
// captureFailure describes it. The banner changes only on user
// actions — start, stop, or an interval change mid-run — never on a
// sampler tick, so unlike the sampler-stats line there is no
// per-second spam risk in announcing it. Stopping deliberately stays
// silent: the user tapped Stop themselves, like Clear, and the banner
// hides without a word. The mid-run interval-change announcement lives
// in tests/native-interval-change-announcement.test.mjs; this test
// covers the start path and the silent stop. This test reads the Swift sources (it cannot
// run Swift in this sandbox) to assert the announcement exists and is
// called from the start path.

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
const announcements = readFileSync(
  new URL(
    "../native/Sources/MetaTrio/Services/AccessibilityAnnouncement.swift",
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
const statsTag = page.match(/<p id="sampler-stats"[^>]*>/);
assert.ok(statsTag, "index.html is missing its sampler-stats element");

const slice = (from, to) => model.slice(model.indexOf(from), model.indexOf(to));
const startAnalysis = slice("func startAnalysis()", "func stopAnalysis()");
const stopAnalysis = slice("func stopAnalysis()", "/// Stops capture");
const analysisStartedFn = announcements.slice(
  announcements.indexOf("static func analysisStarted("),
);

test("web: analysis-active is a polite, atomic live region", () => {
  assert.match(analysisTag[0], /aria-live="polite"/);
  assert.match(analysisTag[0], /aria-atomic="true"/);
});

test("web: sampler-stats stays out of the live regions (it moves every tick)", () => {
  assert.doesNotMatch(statsTag[0], /aria-live/);
});

test("web: the banner text is still set by updateAnalysisActive, hidden while idle", () => {
  assert.ok(
    web.includes("els.analysisActive.hidden = !sampler.running"),
    "updateAnalysisActive no longer hides the banner while idle",
  );
});

test("native: startAnalysis announces the banner's own words when sampling starts", () => {
  assert.ok(
    contentView.includes(
      'accessibilityLabel("Analysis active, sampling one frame every \\(model.intervalSeconds) seconds")',
    ),
    "native banner label changed — the announcement must match it",
  );
  assert.match(
    startAnalysis,
    /if analysisRunning \{\s*AccessibilityAnnouncement\.analysisStarted\("Analysis active, sampling one frame every \\\(intervalSeconds\) seconds"\)/,
  );
});

test("native: stopAnalysis stays silent (the user tapped Stop themselves)", () => {
  assert.doesNotMatch(stopAnalysis, /AccessibilityAnnouncement/);
});

test("native: analysisStarted posts verbatim, not as a backend or capture failure", () => {
  assert.ok(
    analysisStartedFn.includes("post(message)"),
    "analysisStarted does not post verbatim",
  );
  assert.doesNotMatch(analysisStartedFn, /backendFailure|captureFailure/);
});
