// Node built-in test runner, no dependencies:
//   node --test tests/native-ignis-ops-console-headings.test.mjs
//
// OPS-CONSOLE-2 (Del UI direction, Oct 29): native Ignis panel
// headings mirror the web OPS-CONSOLE-1 rule. The web rule gives
// body[data-product="ignis"] .panel h2 uppercase mono, 0.12em
// tracking, a 3px red left border, and 10px left padding, keeping
// 15px/700 — but the native panel titles stayed plain 15pt bold on
// every product, so Ignis never read as a console on the Mac while
// the web panels did. The fix gives all five native panel titles
// (Latest, Event timeline, Still image, Prerecorded video, Settings)
// one shared PanelHeading: on Ignis it renders uppercased in
// monospaced 15pt bold with 1.8pt tracking (0.12em of 15pt) and a 3pt
// Ignis-red (#d92b2b) leading tick with 10pt of room before the
// text; Vigiles takes its own OPS-CONSOLE-7 branch and Medicus its
// own OPS-CONSOLE-10 branch, and the final else is only a defensive
// fallback. The Ignis branch
// keeps the original title as its accessibility label, so VoiceOver
// hears the title in its normal case. No Swift toolchain exists in
// this sandbox, so these are static checks on the shipped Swift and
// CSS.

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

test("web contract: OPS-CONSOLE-1 Ignis panel-h2 rule still present", () => {
  const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
  assert.match(
    css,
    /body\[data-product="ignis"\] \.panel h2 \{\s+font-family: var\(--mono\);\s+text-transform: uppercase;\s+letter-spacing: 0\.12em;\s+border-left: 3px solid #d92b2b;\s+padding-left: 10px;/,
    "web Ignis panel headings stay uppercase mono with red tick",
  );
});

test("native PanelHeading: Ignis branch is uppercase mono 15 bold with 1.8pt tracking", () => {
  const ignis = heading.slice(heading.indexOf("if isIgnis"));
  assert.match(
    ignis,
    /Text\(title\.uppercased\(\)\)\s+\.font\(\.system\(size: 15, weight: \.bold, design: \.monospaced\)\)\s+\.tracking\(1\.8\)/,
    "Ignis title is uppercased monospaced 15pt bold at 1.8pt tracking (0.12em of 15pt)",
  );
});

test("native PanelHeading: Ignis branch carries a 3pt red tick with 10pt of room", () => {
  const ignis = heading.slice(heading.indexOf("if isIgnis"));
  assert.match(
    ignis,
    /HStack\(alignment: \.top, spacing: 10\) \{\s+Rectangle\(\)\s+\.fill\(Color\(red: 217 \/ 255, green: 43 \/ 255, blue: 43 \/ 255\)\)\s+\.frame\(width: 3\)/,
    "Ignis heading is a 3pt #d92b2b tick with 10pt spacing before the text",
  );
});

test("native PanelHeading: Ignis branch keeps the original title for VoiceOver", () => {
  const ignis = heading.slice(heading.indexOf("if isIgnis"));
  assert.match(
    ignis,
    /\.accessibilityLabel\(title\)/,
    "VoiceOver hears the title in its normal case, not the shouted capitals",
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

test("native panel titles: all five use PanelHeading gated on Ignis", () => {
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
      `${title} uses PanelHeading gated on the Ignis product`,
    );
  }
  assert.match(
    timelineView,
    /PanelHeading\(title: "Event timeline", isIgnis: model\.selectedProduct == \.ignis, isVigiles: model\.selectedProduct == \.vigiles, isMedicus: model\.selectedProduct == \.medicus\)/,
    "Event timeline uses PanelHeading gated on the Ignis product",
  );
});

test("native panel titles: Latest and Timeline keep their header traits", () => {
  assert.match(
    contentView,
    /PanelHeading\(title: "Latest assessment", isIgnis: model\.selectedProduct == \.ignis, isVigiles: model\.selectedProduct == \.vigiles, isMedicus: model\.selectedProduct == \.medicus\)\s+\.accessibilityAddTraits\(\.isHeader\)/,
    "Latest heading keeps its header trait",
  );
  assert.match(
    timelineView,
    /PanelHeading\(title: "Event timeline", isIgnis: model\.selectedProduct == \.ignis, isVigiles: model\.selectedProduct == \.vigiles, isMedicus: model\.selectedProduct == \.medicus\)\s+\.accessibilityAddTraits\(\.isHeader\)/,
    "Timeline heading keeps its header trait",
  );
});

test("native panel titles: no plain 15pt-bold title Text left behind", () => {
  for (const title of [
    "Latest assessment",
    "Still image",
    "Prerecorded video",
    "Settings",
  ]) {
    assert.doesNotMatch(
      contentView,
      new RegExp(`Text\\("${title}"\\)\\s+\\.font\\(\\.system\\(size: 15, weight: \\.bold\\)\\)`),
      `${title} no longer renders as a bare Text`,
    );
  }
  assert.doesNotMatch(
    timelineView,
    /Text\("Event timeline"\)\s+\.font\(\.system\(size: 15, weight: \.bold\)\)/,
    "Event timeline no longer renders as a bare Text",
  );
});

test("native panel titles: Settings stays a GroupBox label, camera panel untouched", () => {
  assert.match(
    contentView,
    /label: \{[\s\S]*?PanelHeading\(title: "Settings"/,
    "Settings heading is still the GroupBox label",
  );
  assert.doesNotMatch(
    contentView,
    /PanelHeading\(title: "Camera/,
    "camera panel carries no title and gains no heading",
  );
});
