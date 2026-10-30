// Node built-in test runner, no dependencies:
//   node --test tests/native-ignis-ops-console-body.test.mjs
//
// OPS-CONSOLE-4 (Del UI direction, Oct 29): native Ignis Latest-panel
// body treatment mirrors the web OPS-CONSOLE-3 rule. The web rule
// widens Ignis .subhead tracking to 0.08em and frames the
// latest-assessment readout (the mono-block) in Ignis red at 0.4 over
// a dark 0.25 fill — but the native Latest panel kept its UI-12
// subhead tracking on every product and gave its readout viewport
// no frame at all, so Ignis never read as a console on the Mac past
// its panel headings. The fix widens the native Uncertainty heading
// — the established .subhead counterpart — from 0.65pt to 1.04pt
// (0.08em of 13pt) on an Ignis assessment, and frames the native
// readout ScrollView in Ignis red at 0.4 over black at 0.25 when
// Ignis is selected. The heading gate follows the card's own
// product (the UI-5 accent precedent: AssessmentView never consults
// the selected product), while the viewport frame follows the
// selected product (the PanelHeading precedent); on the normal path
// the two agree, and on a redisplayed assessment from another
// product each follows its own established rule. Size, weight, case,
// and color of the heading are untouched, the card's own rule,
// border, and wash are untouched, and the waiting, error, and
// no-assessment placeholders — which sit outside the ScrollView —
// are untouched. The other two OPS-CONSOLE-3 elements are NOT in
// this slice: camera status lines kept their UI-35 13pt contract
// here and gained their status-line treatment in the OPS-CONSOLE-5
// follow-up (see native-ignis-ops-console-status.test.mjs), while
// macOS system buttons own their corner radius, so that element
// stays for a follow-up slice rather than being forced here. No
// Swift toolchain exists in this sandbox, so these are static
// checks on the shipped Swift and CSS.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const contentView = readFileSync(
  new URL("../native/Sources/MetaTrio/Views/ContentView.swift", import.meta.url),
  "utf8",
);
const assessmentView = readFileSync(
  new URL("../native/Sources/MetaTrio/Views/AssessmentView.swift", import.meta.url),
  "utf8",
);

const readout = contentView.slice(
  contentView.indexOf("if let assessment = model.displayedAssessment"),
  contentView.indexOf("} else if model.requestInFlight"),
);
assert.ok(readout.length > 0, "latest-assessment readout block exists");
const uncertaintyHead = assessmentView
  .slice(assessmentView.indexOf("private var uncertaintySection"))
  .slice(0, assessmentView.slice(assessmentView.indexOf("private var uncertaintySection")).indexOf("if response.assessment.uncertainty.isEmpty"));
assert.ok(uncertaintyHead.length > 0, "uncertainty heading block exists");

test("native ops-console body: web contract — OPS-CONSOLE-3 subhead and mono-block frame still present", () => {
  const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
  assert.match(
    css,
    /body\[data-product="ignis"\] \.subhead \{\s+letter-spacing: 0\.08em;/,
    "web Ignis subhead stays at 0.08em tracking",
  );
  assert.match(
    css,
    /body\[data-product="ignis"\] \.mono-block \{\s+border: 1px solid rgba\(217, 43, 43, 0\.4\);\s+background: rgba\(0, 0, 0, 0\.25\);/,
    "web Ignis mono-block frame stays red at 0.4 over dark 0.25",
  );
});

test("native ops-console body: Uncertainty subhead widens to 1.04pt on Ignis, keeps 0.65pt elsewhere", () => {
  assert.match(
    uncertaintyHead,
    /Text\("Uncertainty"\)\s+\.font\(\.system\(size: 13, weight: \.bold\)\)\s+\.textCase\(\.uppercase\)\s+\.tracking\(\(isIgnisAssessment \|\| isVigilesAssessment\) \? 1\.04 : \(isMedicusAssessment \? 0\.78 : 0\.65\)\)\s+\.foregroundStyle\(\.secondary\)\s+\.accessibilityAddTraits\(\.isHeader\)/,
    "Uncertainty heading is 13pt bold uppercase secondary with header trait, tracking 1.04pt on Ignis or Vigiles (OPS-CONSOLE-8 shares the widened value), 0.78pt on Medicus (OPS-CONSOLE-11), and 0.65pt off all three",
  );
  assert.match(
    assessmentView,
    /private var isIgnisAssessment: Bool \{\s+ProductID\(rawValue: response\.product\) == \.ignis\s+\}/,
    "Ignis gate reads the card's own product, not the selected product",
  );
  assert.doesNotMatch(
    assessmentView,
    /selectedProduct/,
    "AssessmentView still never consults the selected product",
  );
});

test("native ops-console body: readout viewport frames in Ignis red at 0.4 over dark 0.25 on Ignis only", () => {
  assert.match(
    readout,
    /ScrollView \{\s+AssessmentView\(response: assessment\)\s+\}\s+\.frame\(maxHeight: 320\)\s+\.background\(\(model\.selectedProduct == \.ignis \|\| model\.selectedProduct == \.vigiles \|\| model\.selectedProduct == \.medicus\) \? Color\.black\.opacity\(0\.25\) : Color\.clear\)/,
    "readout ScrollView keeps its 320pt cap and gains a dark 0.25 fill on Ignis, Vigiles (OPS-CONSOLE-8), and Medicus (OPS-CONSOLE-11, sharing one fill), clear elsewhere",
  );
  assert.match(
    readout,
    /\.overlay \{\s+if model\.selectedProduct == \.ignis \{\s+Rectangle\(\)\s+\.stroke\(Color\(red: 217 \/ 255, green: 43 \/ 255, blue: 43 \/ 255\)\.opacity\(0\.4\), lineWidth: 1\)/,
    "readout ScrollView gains a 1pt Ignis-red 0.4 stroke on Ignis only",
  );
});

test("native ops-console body: placeholders and card treatment untouched", () => {
  assert.match(
    contentView,
    /Text\("Waiting for the first assessment…"\)\s+\.font\(\.system\(size: 13, design: \.monospaced\)\)/,
    "waiting placeholder keeps its 13pt mono treatment",
  );
  assert.match(
    contentView,
    /Text\("No assessment received yet\."\)\s+\.font\(\.system\(size: 13, design: \.monospaced\)\)/,
    "no-assessment placeholder keeps its 13pt mono treatment",
  );
  assert.doesNotMatch(
    readout,
    /opacity\(0\.25\)[\s\S]*opacity\(0\.25\)/,
    "no second dark fill is stacked inside the readout",
  );
});

test("native ops-console body: Observations heading gains nothing; camera state lines moved to OPS-CONSOLE-5", () => {
  const observationsFn = assessmentView.slice(
    assessmentView.indexOf("private var observationsSection"),
    assessmentView.indexOf("private var uncertaintySection"),
  );
  assert.doesNotMatch(
    observationsFn,
    /isIgnisAssessment/,
    "Observations heading gains no Ignis treatment",
  );
  // OPS-CONSOLE-5 rewired this assertion: the state lines kept
  // their UI-35 13pt size and gained the conditional mono face
  // and 0.26pt tracking there, so the plain-font form this test
  // used to assert no longer exists. OPS-CONSOLE-9 widened the
  // gate to Ignis or Vigiles, and this assertion was rewired to
  // the two-gate form. OPS-CONSOLE-12 widened it to all three,
  // and this assertion was rewired to the three-gate form. The full treatment is covered by
  // native-ignis-ops-console-status.test.mjs.
  assert.match(
    contentView,
    /Text\("Camera is off\."\)\s+\.font\(\.system\(size: 13, design: \(isIgnisSelected \|\| isVigilesSelected \|\| isMedicusSelected\) \? \.monospaced : \.default\)\)\s+\.tracking\(\(isIgnisSelected \|\| isVigilesSelected \|\| isMedicusSelected\) \? 0\.26 : 0\)/,
    "camera state lines now carry the OPS-CONSOLE-5 conditional mono face and tracking at 13pt, widened to Vigiles by OPS-CONSOLE-9 and to Medicus by OPS-CONSOLE-12",
  );
});
