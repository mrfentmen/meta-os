// Node built-in test runner, no dependencies:
//   node --test tests/native-ignis-assessment-summary-size.test.mjs
//
// IGNIS-UI-20 (Del UI push, Oct 29): native latest-assessment panel
// summary size parity. The web panel renders the summary as a plain
// <p> at the 15px body size — styles.css sets body font-size 15px and
// js/app.js gives the paragraph no class — but the native summary was
// a plain Text at the default body size, so it read smaller than the
// web paragraph while the category, subline, and processing line
// already matched their own web rules. The fix gives the summary a
// 15pt system font, keeping its non-empty guard and wording. No Swift
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

const summaryBlock = assessment.slice(
  assessment.indexOf("if !response.assessment.summary.isEmpty"),
  assessment.indexOf("observationsSection"),
);
assert.ok(summaryBlock.length > 0, "summary block exists");

test("native summary: 15pt system font, guard unchanged", () => {
  assert.match(
    summaryBlock,
    /if !response\.assessment\.summary\.isEmpty \{\s+\/\/ UI-20[\s\S]*?Text\(response\.assessment\.summary\)\s+\.font\(\.system\(size: 15\)\)/,
    "summary keeps its non-empty guard, then takes the 15pt font",
  );
});

test("native summary: web contract — plain paragraph at 15px body size", () => {
  const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
  assert.match(
    css,
    /body \{\s+margin: 0;\s+background: var\(--bg\);\s+color: var\(--text\);\s+font-family: system-ui[^;]*;\s+font-size: 15px;/,
    "web body size is 15px",
  );
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  assert.match(
    app,
    /if \(assessment\.assessment\.summary !== ""\) \{\s+const text = document\.createElement\("p"\);\s+text\.textContent = assessment\.assessment\.summary;/,
    "web summary is a plain paragraph with no size class",
  );
});

test("native summary: neighbors keep their sizes", () => {
  assert.match(
    assessment,
    /Text\(response\.assessment\.category\)\s+\.font\(\.title3\)/,
    "category keeps its title3 size",
  );
  assert.match(
    assessment,
    /\.font\(\.system\(size: 12\.5\)\)/,
    "subline keeps its 12.5pt size (UI-19)",
  );
  assert.match(
    assessment,
    /\.font\(\.system\(size: 12\.5, design: \.monospaced\)\)/,
    "processing line keeps its 12.5pt monospace font (UI-15)",
  );
});

test("native summary: exactly one plain 15pt font in the summary block", () => {
  // Superseded scope, not dropped: this guard once counted one plain
  // 15pt font in the whole file, but the uncertainty section now
  // carries its own 15pt fonts, governed by
  // tests/native-ignis-assessment-uncertainty-size.test.mjs. The
  // summary block itself still carries exactly one.
  const plain = summaryBlock.match(/\.font\(\.system\(size: 15\)\)/g) || [];
  assert.equal(plain.length, 1, "exactly one plain 15pt font in the summary block");
});
