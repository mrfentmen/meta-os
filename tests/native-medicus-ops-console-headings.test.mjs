// Node built-in test runner, no dependencies:
//   node --test tests/native-medicus-ops-console-headings.test.mjs
//
// OPS-CONSOLE-10 (Del UI direction, Oct 29): native Medicus panel
// headings mirror the web Medicus ops-console rule. The web rule gives
// body[data-product="medicus"] .panel h2 uppercase with 0.08em
// tracking and nothing else — no mono face, no left border — but the
// native panel titles stayed plain 15pt bold on Medicus, so Medicus
// never read as a console on the Mac while the web panels did. The fix
// adds a Medicus branch to the shared PanelHeading: on Medicus it
// renders uppercased in plain 15pt bold with 1.2pt tracking (0.08em of
// 15pt), deliberately softer than the Ignis/Vigiles 1.8pt console
// branches and with no tick, because the web Medicus rule carries
// none. The Medicus branch keeps the original title as its
// accessibility label, so VoiceOver hears the title in its normal
// case. The final else is now only a defensive fallback — all three
// products are gated, so no product renders it in practice. No Swift
// toolchain exists in this sandbox, so these are static checks on the
// shipped Swift and CSS.

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

const medicus = heading.slice(
  heading.indexOf("else if isMedicus"),
  heading.indexOf("} else {"),
);
assert.ok(medicus.length > 0, "PanelHeading has a Medicus branch");

test("web contract: Medicus panel-h2 rule still present", () => {
  const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
  assert.match(
    css,
    /body\[data-product="medicus"\] \.panel h2 \{\s+text-transform: uppercase;\s+letter-spacing: 0\.08em;/,
    "web Medicus panel headings stay uppercase with 0.08em tracking",
  );
});

test("native PanelHeading: Medicus branch is uppercase plain 15 bold with 1.2pt tracking", () => {
  assert.match(
    medicus,
    /Text\(title\.uppercased\(\)\)\s+\.font\(\.system\(size: 15, weight: \.bold\)\)\s+\.tracking\(1\.2\)/,
    "Medicus title is uppercased plain 15pt bold at 1.2pt tracking (0.08em of 15pt)",
  );
});

test("native PanelHeading: Medicus branch carries no mono face and no tick", () => {
  assert.doesNotMatch(medicus, /\.monospaced/, "no mono face on Medicus headings");
  assert.doesNotMatch(medicus, /Rectangle/, "no tick on Medicus headings");
  assert.doesNotMatch(
    medicus,
    /217 \/ 255, green: 43 \/ 255, blue: 43 \/ 255/,
    "no Ignis red in the Medicus branch",
  );
  assert.doesNotMatch(
    medicus,
    /79 \/ 255, green: 126 \/ 255, blue: 194 \/ 255/,
    "no Vigiles blue in the Medicus branch",
  );
});

test("native PanelHeading: Medicus branch keeps the original title for VoiceOver", () => {
  assert.match(
    medicus,
    /\.accessibilityLabel\(title\)/,
    "VoiceOver hears the title in its normal case, not the shouted capitals",
  );
});

test("native PanelHeading: fallback else still renders the plain 15pt bold title", () => {
  const plain = heading.slice(heading.indexOf("} else {"));
  assert.match(
    plain,
    /Text\(title\)\s+\.font\(\.system\(size: 15, weight: \.bold\)\)/,
    "ungated fallback is the same plain 15pt bold title as before",
  );
  assert.doesNotMatch(plain, /uppercased/, "no case change on the fallback");
  assert.doesNotMatch(plain, /tracking/, "no tracking on the fallback");
  assert.doesNotMatch(plain, /Rectangle/, "no tick on the fallback");
});

test("native panel titles: all five use PanelHeading gated on Medicus", () => {
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
      `${title} uses PanelHeading gated on the Medicus product`,
    );
  }
  assert.match(
    timelineView,
    /PanelHeading\(title: "Event timeline", isIgnis: model\.selectedProduct == \.ignis, isVigiles: model\.selectedProduct == \.vigiles, isMedicus: model\.selectedProduct == \.medicus\)/,
    "Event timeline uses PanelHeading gated on the Medicus product",
  );
});

test("native panel titles: camera panel untouched, no Medicus heading for it", () => {
  assert.doesNotMatch(
    contentView,
    /PanelHeading\(title: "Camera/,
    "camera panel carries no title and gains no heading",
  );
});

test("native PanelHeading: Ignis and Vigiles branches unchanged", () => {
  assert.match(
    heading,
    /Text\(title\.uppercased\(\)\)\s+\.font\(\.system\(size: 15, weight: \.bold, design: \.monospaced\)\)\s+\.tracking\(1\.8\)/,
    "Ignis and Vigiles keep their uppercase mono 15pt bold at 1.8pt tracking",
  );
  assert.match(
    heading,
    /Color\(red: 217 \/ 255, green: 43 \/ 255, blue: 43 \/ 255\)/,
    "Ignis red tick still present",
  );
  assert.match(
    heading,
    /Color\(red: 79 \/ 255, green: 126 \/ 255, blue: 194 \/ 255\)/,
    "Vigiles blue tick still present",
  );
});
