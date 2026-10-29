// Node built-in test runner, no dependencies:
//   node --test tests/native-ignis-assessment-subhead.test.mjs
//
// IGNIS-UI-12 (Del UI push, Oct 29): native latest-assessment panel
// uncertainty-heading parity. The web panel renders its Uncertainty
// heading with class "subhead" — 13px, weight 700, uppercase,
// letter-spacing 0.05em, muted — but the native heading used .headline
// (17pt semibold, no case or tracking, default color), so it read as a
// body section title while the web heading read as a small muted label
// above the uncertainty items. The fix styles the native Uncertainty
// heading as 13pt bold, uppercase, 0.65pt tracking (0.05em of 13pt),
// secondary (the system stand-in for the web --muted gray), keeping
// the header trait. The Observations heading is untouched: the web
// panel renders observations as a bare list with no heading, so there
// is no web counterpart to mirror there. No Swift toolchain exists in
// this sandbox, so these are static checks on the shipped Swift.

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

const uncertaintyFn = assessment.slice(
  assessment.indexOf("private var uncertaintySection"),
);
assert.ok(uncertaintyFn.length > 0, "uncertaintySection exists");
const uncertaintyHead = uncertaintyFn.slice(
  0,
  uncertaintyFn.indexOf("if response.assessment.uncertainty.isEmpty"),
);
assert.ok(uncertaintyHead.length > 0, "uncertainty heading block exists");

test("native uncertainty heading: subhead size, weight, case, tracking, muted color", () => {
  assert.match(
    uncertaintyHead,
    /Text\("Uncertainty"\)\s+\.font\(\.system\(size: 13, weight: \.bold\)\)\s+\.textCase\(\.uppercase\)\s+\.tracking\(0\.65\)\s+\.foregroundStyle\(\.secondary\)\s+\.accessibilityAddTraits\(\.isHeader\)/,
    "Uncertainty heading is 13pt bold, uppercase, 0.65pt tracking, secondary, and keeps the header trait",
  );
});

test("native uncertainty heading: web .subhead rule and web heading class match", () => {
  const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
  assert.match(
    css,
    /\.subhead \{\s+margin: 14px 0 6px;\s+font-size: 13px;\s+font-weight: 700;\s+color: var\(--muted\);\s+text-transform: uppercase;\s+letter-spacing: 0\.05em;/,
    "web .subhead is 13px, weight 700, muted, uppercase, 0.05em tracking",
  );
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  assert.match(
    app,
    /uncertaintyHead\.className = "subhead";/,
    "web Uncertainty heading carries the subhead class",
  );
});

test("native uncertainty heading: exactly one subhead-styled heading, Observations untouched", () => {
  const subheads = assessment.match(
    /\.font\(\.system\(size: 13, weight: \.bold\)\)/g,
  ) || [];
  assert.equal(subheads.length, 1, "exactly one 13pt bold heading — the Uncertainty heading");
  const observationsFn = assessment.slice(
    assessment.indexOf("private var observationsSection"),
    assessment.indexOf("private var uncertaintySection"),
  );
  assert.match(
    observationsFn,
    /Text\("Observations"\)\s+\.font\(\.headline\)/,
    "Observations heading still uses .headline — the web list has no heading to mirror",
  );
  assert.doesNotMatch(
    observationsFn,
    /\.textCase\(\.uppercase\)/,
    "Observations heading gains no uppercase treatment",
  );
});

test("native uncertainty heading: styling tracks no accent and no selected product", () => {
  assert.doesNotMatch(
    uncertaintyHead,
    /accentColor/,
    "heading styling uses no product accent",
  );
  assert.doesNotMatch(
    assessment,
    /selectedProduct/,
    "AssessmentView never consults the selected product",
  );
});
