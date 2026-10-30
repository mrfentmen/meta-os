// Node built-in test runner, no dependencies:
//   node --test tests/native-medicus-ops-console-body.test.mjs
//
// OPS-CONSOLE-11 (Del UI direction, Oct 29): native Medicus
// Latest-panel body treatment mirrors the web Medicus rule.
// The web rule widens Medicus .subhead tracking to 0.06em and
// frames the latest-assessment readout (the mono-block) in Medicus
// green at 0.4 over a dark 0.25 fill — but the native Latest panel
// kept its UI-12 subhead tracking on a Medicus assessment and gave
// its readout viewport no frame on Medicus, so Medicus never read
// as a console on the Mac past its panel headings (OPS-CONSOLE-10).
// The fix widens the native Uncertainty heading — the established
// .subhead counterpart — from 0.65pt to 0.78pt (0.06em of 13pt) on
// a Medicus assessment, taking its own middle value rather than
// sharing the Ignis/Vigiles 1.04pt, and frames the native readout
// ScrollView in Medicus green at 0.4 over black at 0.25 when
// Medicus is selected. The heading gate follows the card's own
// product (the UI-5 accent precedent: AssessmentView never
// consults the selected product), while the viewport frame follows
// the selected product (the PanelHeading precedent); on the normal
// path the two agree, and on a redisplayed assessment from another
// product each follows its own established rule. The dark 0.25 fill
// is one condition shared by Ignis, Vigiles, and Medicus, not three
// fills stacked; the stroke keeps one branch per product so each
// accent stays its own color. Size, weight, case, and color of the
// heading are untouched, the card's own rule, border, and wash are
// untouched, and the waiting, error, and no-assessment placeholders
// — which sit outside the ScrollView — are untouched. The other
// Medicus console elements are NOT in this slice: camera status
// lines keep their two-gate Ignis/Vigiles treatment here and gain
// their Medicus treatment in a follow-up slice, while macOS system
// buttons own their corner radius, so that element stays for a
// follow-up slice rather than being forced here. No Swift toolchain
// exists in this sandbox, so these are static checks on the shipped
// Swift and CSS.

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

test("native ops-console body: web contract — Medicus subhead and mono-block frame still present", () => {
  const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
  assert.match(
    css,
    /body\[data-product="medicus"\] \.subhead \{\s+text-transform: uppercase;\s+letter-spacing: 0\.06em;/,
    "web Medicus subhead stays uppercase at 0.06em tracking",
  );
  assert.match(
    css,
    /body\[data-product="medicus"\] \.mono-block \{\s+border: 1px solid rgba\(93, 168, 100, 0\.4\);\s+background: rgba\(0, 0, 0, 0\.25\);/,
    "web Medicus mono-block frame stays green at 0.4 over dark 0.25",
  );
});

test("native ops-console body: Uncertainty subhead widens to 0.78pt on Medicus, keeps 1.04pt on Ignis/Vigiles and 0.65pt elsewhere", () => {
  assert.match(
    uncertaintyHead,
    /Text\("Uncertainty"\)\s+\.font\(\.system\(size: 13, weight: \.bold\)\)\s+\.textCase\(\.uppercase\)\s+\.tracking\(\(isIgnisAssessment \|\| isVigilesAssessment\) \? 1\.04 : \(isMedicusAssessment \? 0\.78 : 0\.65\)\)\s+\.foregroundStyle\(\.secondary\)\s+\.accessibilityAddTraits\(\.isHeader\)/,
    "Uncertainty heading is 13pt bold uppercase secondary with header trait, tracking 0.78pt on Medicus, 1.04pt on Ignis or Vigiles, and 0.65pt off all three",
  );
  assert.match(
    assessmentView,
    /private var isMedicusAssessment: Bool \{\s+ProductID\(rawValue: response\.product\) == \.medicus\s+\}/,
    "Medicus gate reads the card's own product, not the selected product",
  );
  assert.doesNotMatch(
    assessmentView,
    /selectedProduct/,
    "AssessmentView still never consults the selected product",
  );
});

test("native ops-console body: readout viewport frames in Medicus green at 0.4 over dark 0.25 on Medicus only", () => {
  assert.match(
    readout,
    /ScrollView \{\s+AssessmentView\(response: assessment\)\s+\}\s+\.frame\(maxHeight: 320\)\s+\.background\(\(model\.selectedProduct == \.ignis \|\| model\.selectedProduct == \.vigiles \|\| model\.selectedProduct == \.medicus\) \? Color\.black\.opacity\(0\.25\) : Color\.clear\)/,
    "readout ScrollView keeps its 320pt cap and gains a dark 0.25 fill on Ignis, Vigiles, or Medicus, clear elsewhere",
  );
  assert.match(
    readout,
    /\.overlay \{\s+if model\.selectedProduct == \.ignis \{\s+Rectangle\(\)\s+\.stroke\(Color\(red: 217 \/ 255, green: 43 \/ 255, blue: 43 \/ 255\)\.opacity\(0\.4\), lineWidth: 1\)\s+\}\s+if model\.selectedProduct == \.vigiles \{\s+Rectangle\(\)\s+\.stroke\(Color\(red: 79 \/ 255, green: 126 \/ 255, blue: 194 \/ 255\)\.opacity\(0\.4\), lineWidth: 1\)\s+\}\s+if model\.selectedProduct == \.medicus \{\s+Rectangle\(\)\s+\.stroke\(Color\(red: 93 \/ 255, green: 168 \/ 255, blue: 100 \/ 255\)\.opacity\(0\.4\), lineWidth: 1\)/,
    "readout ScrollView keeps its 1pt Ignis-red and Vigiles-blue 0.4 strokes and gains a 1pt Medicus-green 0.4 stroke on Medicus",
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
  assert.equal(
    (readout.match(/opacity\(0\.25\)/g) || []).length,
    1,
    "exactly one dark 0.25 fill in the readout — Ignis, Vigiles, and Medicus share it, none is stacked",
  );
});

test("native ops-console body: Observations heading gains nothing; camera state lines gain the Medicus status treatment (OPS-CONSOLE-12)", () => {
  const observationsFn = assessmentView.slice(
    assessmentView.indexOf("private var observationsSection"),
    assessmentView.indexOf("private var uncertaintySection"),
  );
  assert.doesNotMatch(
    observationsFn,
    /isMedicusAssessment/,
    "Observations heading gains no Medicus treatment",
  );
  assert.match(
    contentView,
    /Text\("Camera is off\."\)\s+\.font\(\.system\(size: 13, design: \(isIgnisSelected \|\| isVigilesSelected \|\| isMedicusSelected\) \? \.monospaced : \.default\)\)\s+\.tracking\(\(isIgnisSelected \|\| isVigilesSelected \|\| isMedicusSelected\) \? 0\.26 : 0\)/,
    "camera state lines now carry the three-gate Ignis/Vigiles/Medicus conditional mono face and tracking at 13pt — Medicus status lands in OPS-CONSOLE-12",
  );
});
