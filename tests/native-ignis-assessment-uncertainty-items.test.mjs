// Node built-in test runner, no dependencies:
//   node --test tests/native-ignis-assessment-uncertainty-items.test.mjs
//
// IGNIS-UI-14 (Del UI push, Oct 29): native latest-assessment panel
// uncertainty-items parity. The web panel renders its uncertainty list
// with class "uncertainty" — color var(--muted) — but the native items
// used the default text color while the UI-12 heading and the empty
// "no uncertainty items" note both already read muted, so a populated
// list read bolder than the web list and inconsistent with its own
// section. The fix puts .foregroundStyle(.secondary) on the item row
// so bullet and item share the muted color, exactly like web list
// items inheriting the list color. No Swift toolchain exists in this
// sandbox, so these are static checks on the shipped Swift.

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
const itemsBlock = uncertaintyFn.slice(
  uncertaintyFn.indexOf("ForEach(Array(response.assessment.uncertainty"),
);
assert.ok(itemsBlock.length > 0, "uncertainty items ForEach exists");

test("native uncertainty items: item row is muted, bullet and item share it", () => {
  assert.match(
    itemsBlock,
    /HStack\(alignment: \.top, spacing: 6\) \{\s+Text\("•"\)\s+Text\(item\)\s+\}\s+\.foregroundStyle\(\.secondary\)/,
    "uncertainty item row carries .foregroundStyle(.secondary) after the bullet/item HStack",
  );
});

test("native uncertainty items: web .uncertainty rule is muted", () => {
  const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
  assert.match(
    css,
    /\.uncertainty \{\s+color: var\(--muted\);/,
    "web .uncertainty is muted",
  );
  const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
  assert.match(
    app,
    /uncertainty\.className = "uncertainty";/,
    "web uncertainty list carries the uncertainty class",
  );
});

test("native uncertainty items: heading and empty note stay muted, no accent", () => {
  assert.match(
    uncertaintyFn,
    /Text\("Uncertainty"\)\s+\.font\(\.system\(size: 13, weight: \.bold\)\)\s+\.textCase\(\.uppercase\)\s+\.tracking\(0\.65\)\s+\.foregroundStyle\(\.secondary\)/,
    "UI-12 heading still muted",
  );
  assert.match(
    uncertaintyFn,
    /Text\("The model reported no uncertainty items\."\)\s+\.foregroundStyle\(\.secondary\)/,
    "empty note still muted",
  );
  assert.doesNotMatch(
    itemsBlock,
    /accentColor/,
    "uncertainty items track no product accent",
  );
});

test("native uncertainty items: exactly one muted item row, observations untouched", () => {
  const rows = uncertaintyFn.match(
    /HStack\(alignment: \.top, spacing: 6\) \{\s+Text\("•"\)\s+Text\(item\)\s+\}\s+\.foregroundStyle\(\.secondary\)/g,
  ) || [];
  assert.equal(rows.length, 1, "exactly one muted uncertainty item row");
  const observationsFn = assessment.slice(
    assessment.indexOf("private var observationsSection"),
    assessment.indexOf("private var uncertaintySection"),
  );
  assert.doesNotMatch(
    observationsFn,
    /HStack\(alignment: \.top, spacing: 6\)/,
    "observations gain no bullet-row treatment",
  );
});
