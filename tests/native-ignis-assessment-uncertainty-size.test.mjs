// Node built-in test runner, no dependencies:
//   node --test tests/native-ignis-assessment-uncertainty-size.test.mjs
//
// Native latest-assessment panel uncertainty size parity. The web panel
// renders uncertainty at the 15px body size — styles.css gives
// .uncertainty only the muted color, so both the populated list and
// the empty note inherit body 15px — but the native section was plain
// Text at the default size, so both read smaller than the web section
// while the heading (UI-12) and the processing line (UI-15) already
// matched their own web rules. The fix gives the populated row and the
// empty note a 15pt system font, the same default-size gap UI-20
// closed for the summary. No Swift toolchain exists in this sandbox,
// so these are static checks on the shipped Swift.

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

const uncertaintyBlock = assessment.slice(
  assessment.indexOf("private var uncertaintySection"),
  assessment.indexOf("private var processingLine"),
);
assert.ok(uncertaintyBlock.length > 0, "uncertainty section exists");

test("native uncertainty items: 15pt system font on the row", () => {
  assert.match(
    uncertaintyBlock,
    /HStack\(alignment: \.top, spacing: 6\) \{[\s\S]*?Text\("•"\)[\s\S]*?Text\(item\)[\s\S]*?\}\s+\.foregroundStyle\(\.secondary\)\s+\.font\(\.system\(size: 15\)\)/,
    "populated row keeps its bullet and item, muted color, then takes the 15pt font",
  );
});

test("native uncertainty empty note: 15pt system font, wording unchanged", () => {
  assert.match(
    uncertaintyBlock,
    /Text\("The model reported no uncertainty items\."\)\s+\.foregroundStyle\(\.secondary\)\s+\.font\(\.system\(size: 15\)\)/,
    "empty note keeps its wording and muted color, then takes the 15pt font",
  );
});

test("native uncertainty: web contract — list and note at 15px body size", () => {
  const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
  assert.match(
    css,
    /body \{\s+margin: 0;\s+background: var\(--bg\);\s+color: var\(--text\);\s+font-family: system-ui[^;]*;\s+font-size: 15px;/,
    "web body size is 15px",
  );
  assert.match(
    css,
    /\.uncertainty \{\s+color: var\(--muted\);\s+\}/,
    "web .uncertainty sets only the muted color, so it inherits the body size",
  );
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  assert.match(
    app,
    /uncertainty\.className = "uncertainty";/,
    "web uncertainty list and empty note both carry class uncertainty",
  );
});

test("native uncertainty: neighbors keep their sizes", () => {
  assert.match(
    uncertaintyBlock,
    /Text\("Uncertainty"\)\s+\.font\(\.system\(size: 13, weight: \.bold\)\)/,
    "uncertainty heading keeps its 13pt size (UI-12)",
  );
  assert.match(
    assessment,
    /Text\("Model: \\\(response\.processing\.model\) · Server-reported latency: \\\(serverLatencyText\)"\)\s+\.font\(\.system\(size: 12\.5, design: \.monospaced\)\)/,
    "processing line keeps its 12.5pt mono size (UI-15)",
  );
});
