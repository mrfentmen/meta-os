// Node built-in test runner, no dependencies:
//   node --test tests/latest-panel-divider.test.mjs
//
// HANA Agent1: the Latest assessment panel's divider — the web
// counterpart to the native AssessmentView Divider, which sits
// between the uncertainty section and the processing line, so the
// model and server-latency line reads as footer metadata, not as
// another finding. The web panel ran the processing line straight
// after the uncertainty list (or its "no uncertainty items" note)
// with no rule at all, so the footer blended into the findings.
// The fix inserts one aria-hidden <hr> in renderLatest, after the
// uncertainty block and before the processing paragraph, styled
// with the neutral panel border — never a product accent, so a
// redisplayed assessment under another product keeps the same
// neutral rule, like the native Divider, which tracks no accent.
// No Swift toolchain exists in this sandbox, so these are static
// checks on the shipped web sources and the shipped Swift.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");
const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
const native = readFileSync(
  new URL(
    "../native/Sources/MetaTrio/Views/AssessmentView.swift",
    import.meta.url,
  ),
  "utf8",
);

const render = app.slice(
  app.indexOf("function renderLatest"),
  app.indexOf("function addHistoryItem"),
);
assert.ok(render.length > 0, "renderLatest exists");

test("web: Latest panel inserts one divider between uncertainty and processing", () => {
  const creations = render.match(/document\.createElement\("hr"\)/g) || [];
  assert.equal(creations.length, 1, "exactly one hr in renderLatest");
  assert.match(
    render,
    /const divider = document\.createElement\("hr"\);\s+divider\.className = "assessment-divider";\s+divider\.setAttribute\("aria-hidden", "true"\);\s+wrap\.appendChild\(divider\);/,
    "divider carries the assessment-divider class and is aria-hidden",
  );
  const dividerAt = render.indexOf('const divider = document.createElement("hr")');
  const processingAt = render.indexOf('const processing = document.createElement("p")');
  assert.ok(dividerAt > 0 && processingAt > dividerAt, "divider precedes the processing line");
  assert.ok(
    render.indexOf("uncertaintyHead") < dividerAt,
    "divider follows the uncertainty section",
  );
});

test("web: Latest panel divider is a neutral panel-border rule, not an accent", () => {
  const rule = css.match(/\.assessment-divider \{[^}]*\}/);
  assert.ok(rule, "assessment-divider rule exists");
  assert.match(
    rule[0],
    /border-top: 1px solid var\(--panel-border\);/,
    "1px neutral panel-border rule, like the native Divider",
  );
  assert.match(rule[0], /margin: 12px 0;/, "12px gaps, the native stack spacing");
  assert.doesNotMatch(rule[0], /--accent/, "divider tracks no product accent");
  assert.doesNotMatch(
    rule[0],
    /#4f7ec2|#d92b2b|#5da864/,
    "divider uses no fixed product color either",
  );
});

test("native: AssessmentView still carries its Divider in the same place", () => {
  const body = native.slice(native.indexOf("var body: some View"));
  const uncertaintyAt = body.indexOf("uncertaintySection");
  const dividerAt = body.indexOf("Divider()");
  const processingAt = body.indexOf("processingLine");
  assert.ok(
    uncertaintyAt > 0 && dividerAt > uncertaintyAt && processingAt > dividerAt,
    "native Divider still sits between uncertainty and processing",
  );
});
