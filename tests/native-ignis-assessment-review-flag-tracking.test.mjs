// Node built-in test runner, no dependencies:
//   node --test tests/native-ignis-assessment-review-flag-tracking.test.mjs
//
// IGNIS-UI-16 (Del UI push, Oct 29): native latest-assessment panel
// review-flag tracking parity. The web panel renders its review flag
// with class "review-flag" — 12px, weight 700, warn color,
// letter-spacing 0.05em — but the native Label used .caption (12pt),
// bold, and .orange while carrying no tracking, so the flag read
// tighter than the web's letterspaced flag. The fix adds 0.6pt
// tracking (0.05em of 12pt) to the native flag, keeping its uppercase
// literal text, icon, weight, and warn color untouched. No Swift
// toolchain exists in this sandbox, so these are static checks on the
// shipped Swift.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const assessment = readFileSync(
  new URL(
    "../native/Sources/MetaTrio/Views/AssessmentView.swift",
    import.meta.url,
  ),
  "utf8",
);

const headerFn = assessment.slice(
  assessment.indexOf("private var header"),
  assessment.indexOf("private var productDisplayName"),
);
assert.ok(headerFn.length > 0, "header exists");
const flagBlock = headerFn.slice(
  headerFn.indexOf("if response.assessment.requiresHumanReview"),
  headerFn.indexOf("Spacer()"),
);
assert.ok(flagBlock.length > 0, "review flag block exists");

test("native review flag: 0.6pt tracking, size, weight, warn color kept", () => {
  assert.match(
    flagBlock,
    /Label\("REQUIRES HUMAN REVIEW", systemImage: "exclamationmark\.triangle\.fill"\)\s+\.font\(\.caption\)\s+\.fontWeight\(\.bold\)\s+\.tracking\(0\.6\)\s+\.foregroundStyle\(\.orange\)/,
    "review flag is caption, bold, 0.6pt tracking, orange",
  );
});

test("native review flag: web .review-flag rule is 12px, 700, warn, 0.05em", () => {
  const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
  assert.match(
    css,
    /\.review-flag \{\s+color: var\(--warn\);\s+font-weight: 700;\s+font-size: 12px;\s+letter-spacing: 0\.05em;/,
    "web .review-flag is warn, 700, 12px, 0.05em tracking",
  );
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  assert.match(
    app,
    /flag\.className = "review-flag";\s+flag\.textContent = " REQUIRES HUMAN REVIEW";/,
    "web flag carries the review-flag class and the uppercase literal",
  );
});

test("native review flag: text, icon, and color unchanged, no accent", () => {
  assert.match(
    flagBlock,
    /Label\("REQUIRES HUMAN REVIEW", systemImage: "exclamationmark\.triangle\.fill"\)/,
    "flag keeps its uppercase literal and warning icon",
  );
  assert.doesNotMatch(
    flagBlock,
    /accentColor/,
    "flag tracks no product accent",
  );
});

test("native review flag: exactly one 0.6pt tracking, subhead tracking untouched", () => {
  const trackings = assessment.match(/\.tracking\(0\.6\)/g) || [];
  assert.equal(trackings.length, 1, "exactly one 0.6pt tracking in the file");
  assert.match(
    assessment,
    /\.tracking\(\(isIgnisAssessment \|\| isVigilesAssessment\) \? 1\.04 : 0\.65\)/,
    "Uncertainty subhead keeps its 0.65pt non-console tracking (UI-12) and widens to 1.04pt on Ignis (OPS-CONSOLE-4) or Vigiles (OPS-CONSOLE-8)",
  );
  const observationsFn = assessment.slice(
    assessment.indexOf("private var observationsSection"),
    assessment.indexOf("private var uncertaintySection"),
  );
  assert.doesNotMatch(
    observationsFn,
    /\.tracking\(/,
    "Observations heading gains no tracking",
  );
});
