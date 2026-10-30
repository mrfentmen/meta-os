// Node built-in test runner, no dependencies:
//   node --test tests/native-vigiles-ops-console-headings.test.mjs
//
// OPS-CONSOLE-7 (Del UI direction, Oct 29): native Vigiles panel
// headings mirror the web OPS-CONSOLE-6 rule. The web rule gives
// body[data-product="vigiles"] .panel h2 uppercase mono, 0.12em
// tracking, a 3px blue left border, and 10px left padding, keeping
// 15px/700 — but the native panel titles stayed plain 15pt bold on
// Vigiles, so Vigiles never read as a console on the Mac while the
// web panels did. The fix adds a Vigiles branch to the shared
// PanelHeading: on Vigiles it renders uppercased in monospaced 15pt
// bold with 1.8pt tracking (0.12em of 15pt) and a 3pt Vigiles-blue
// (#4f7ec2) leading tick with 10pt of room before the text; Medicus
// takes its own OPS-CONSOLE-10 branch, and the final else is only a
// defensive fallback. The Vigiles branch keeps the original
// title as its accessibility label, so VoiceOver hears the title in
// its normal case. No Swift toolchain exists in this sandbox, so
// these are static checks on the shipped Swift and CSS.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const contentView = readFileSync(
  new URL("../native/Sources/MetaTrio/Views/ContentView.swift", import.meta.url),
  "utf8",
);
const timelineView = readFileSync(
  new URL("../native/Sources/MetaTrio/Views/TimelineView.swift", import.meta.url),
  "utf8",
);

const heading = contentView.slice(
  contentView.indexOf("struct PanelHeading"),
  contentView.indexOf("// MARK: - Header"),
);
assert.ok(heading.length > 0, "PanelHeading struct exists");

const vigiles = heading.slice(
  heading.indexOf("else if isVigiles"),
  heading.indexOf("} else {"),
);
assert.ok(vigiles.length > 0, "PanelHeading has a Vigiles branch");

test("web contract: OPS-CONSOLE-6 Vigiles panel-h2 rule still present", () => {
  const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
  assert.match(
    css,
    /body\[data-product="vigiles"\] \.panel h2 \{\s+font-family: var\(--mono\);\s+text-transform: uppercase;\s+letter-spacing: 0\.12em;\s+border-left: 3px solid #4f7ec2;\s+padding-left: 10px;/,
    "web Vigiles panel headings stay uppercase mono with blue tick",
  );
});

test("native PanelHeading: Vigiles branch is uppercase mono 15 bold with 1.8pt tracking", () => {
  assert.match(
    vigiles,
    /Text\(title\.uppercased\(\)\)\s+\.font\(\.system\(size: 15, weight: \.bold, design: \.monospaced\)\)\s+\.tracking\(1\.8\)/,
    "Vigiles title is uppercased monospaced 15pt bold at 1.8pt tracking (0.12em of 15pt)",
  );
});

test("native PanelHeading: Vigiles branch carries a 3pt blue tick with 10pt of room", () => {
  assert.match(
    vigiles,
    /HStack\(alignment: \.top, spacing: 10\) \{\s+Rectangle\(\)\s+\.fill\(Color\(red: 79 \/ 255, green: 126 \/ 255, blue: 194 \/ 255\)\)\s+\.frame\(width: 3\)/,
    "Vigiles heading is a 3pt #4f7ec2 tick with 10pt spacing before the text",
  );
});

test("native PanelHeading: Vigiles branch keeps the original title for VoiceOver", () => {
  assert.match(
    vigiles,
    /\.accessibilityLabel\(title\)/,
    "VoiceOver hears the title in its normal case, not the shouted capitals",
  );
});

test("native PanelHeading: Vigiles branch uses no Ignis red", () => {
  assert.doesNotMatch(
    vigiles,
    /217 \/ 255, green: 43 \/ 255, blue: 43 \/ 255/,
    "Vigiles tick is Vigiles blue, never Ignis red",
  );
});

test("native PanelHeading: ungated fallback still renders the plain 15pt bold title", () => {
  const plain = heading.slice(heading.indexOf("} else {"));
  assert.match(
    plain,
    /Text\(title\)\s+\.font\(\.system\(size: 15, weight: \.bold\)\)/,
    "fallback branch is the same plain 15pt bold title as before",
  );
  assert.doesNotMatch(plain, /uppercased/, "no case change on the fallback");
  assert.doesNotMatch(plain, /tracking/, "no tracking on the fallback");
  assert.doesNotMatch(plain, /Rectangle/, "no tick on the fallback");
});

test("native panel titles: all five use PanelHeading gated on Vigiles", () => {
  for (const title of [
    "Latest assessment",
    "Still image",
    "Prerecorded video",
    "Settings",
  ]) {
    assert.match(
      contentView,
      new RegExp(
        `PanelHeading\\(title: "${title}", isIgnis: model\\.selectedProduct == \\.ignis, isVigiles: model\\.selectedProduct == \\.vigiles, isMedicus: model\\.selectedProduct == \\.medicus\\)`,
      ),
      `${title} uses PanelHeading gated on the Vigiles product`,
    );
  }
  assert.match(
    timelineView,
    /PanelHeading\(title: "Event timeline", isIgnis: model\.selectedProduct == \.ignis, isVigiles: model\.selectedProduct == \.vigiles, isMedicus: model\.selectedProduct == \.medicus\)/,
    "Event timeline uses PanelHeading gated on the Vigiles product",
  );
});

test("native panel titles: camera panel untouched, no Vigiles heading for it", () => {
  assert.doesNotMatch(
    contentView,
    /PanelHeading\(title: "Camera/,
    "camera panel carries no title and gains no heading",
  );
});
