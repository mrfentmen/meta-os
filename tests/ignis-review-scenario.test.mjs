// Node built-in test runner, no dependencies:
//   node --test tests/ignis-review-scenario.test.mjs
//
// IGNIS-ONEOFONE-15 (Del's one-of-one bar, Oct 30): the Ignis
// review queue by scenario label counts only assessments already
// awaiting human review — recorded ok Ignis assessments whose
// assessment itself carried requires_human_review === true —
// split by the scenario_label the log entry itself recorded at
// submit time (the ONEOFONE-10 field, the operator-selected or
// custom label, never inferred after the fact). Real state only:
// clear and unknown-flag entries move no bucket, failures and
// other products move no bucket, and a flagged entry with no
// usable label (missing, empty, or non-string) still counts in
// the total and in unlabeled, never guessed into a bucket. An
// empty or held session reads all zeros. The panel itself lives
// in index.html (hidden under Vigiles/Medicus by styles.css) and
// is rendered from log.entries() inside updateLogStats in
// js/app.js. No contract, server, or Spark-gate change.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { ignisReviewByScenario } from "../js/ignis-review-scenario.js";

const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");

const flagged = (scenarioLabel, overrides = {}) => ({
  status: "ok",
  product: "ignis",
  scenario_label: scenarioLabel,
  response: {
    assessment: { requires_human_review: true },
  },
  ...overrides,
});

test("review by scenario: an empty session reads all zeros", () => {
  assert.deepEqual(ignisReviewByScenario([]), {
    totalFlagged: 0,
    unlabeled: 0,
    byScenario: {},
  });
  assert.deepEqual(ignisReviewByScenario(null), {
    totalFlagged: 0,
    unlabeled: 0,
    byScenario: {},
  });
  assert.deepEqual(ignisReviewByScenario(undefined), {
    totalFlagged: 0,
    unlabeled: 0,
    byScenario: {},
  });
});

test("review by scenario: flagged entries bucket by the exact recorded label", () => {
  assert.deepEqual(
    ignisReviewByScenario([
      flagged("steam-or-fog"),
      flagged("steam-or-fog"),
      flagged("clear-smoke"),
      flagged("custom drill label"),
    ]),
    {
      totalFlagged: 4,
      unlabeled: 0,
      byScenario: {
        "steam-or-fog": 2,
        "clear-smoke": 1,
        "custom drill label": 1,
      },
    },
  );
});

test("review by scenario: missing, empty, and non-string labels count as unlabeled, never guessed", () => {
  assert.deepEqual(
    ignisReviewByScenario([
      flagged(undefined),
      flagged(null),
      flagged(""),
      flagged(42),
      flagged("steam-or-fog"),
    ]),
    {
      totalFlagged: 5,
      unlabeled: 4,
      byScenario: { "steam-or-fog": 1 },
    },
  );
});

test("review by scenario: clear, unknown-flag, failed, and other-product entries move no bucket", () => {
  const counts = ignisReviewByScenario([
    flagged("steam-or-fog", {
      response: { assessment: { requires_human_review: false } },
    }),
    flagged("steam-or-fog", {
      response: { assessment: {} },
    }),
    flagged("steam-or-fog", { status: "network_error" }),
    flagged("steam-or-fog", { product: "vigiles" }),
    flagged("steam-or-fog", { product: "medicus" }),
    flagged("steam-or-fog"),
  ]);
  assert.deepEqual(counts, {
    totalFlagged: 1,
    unlabeled: 0,
    byScenario: { "steam-or-fog": 1 },
  });
});

test("review by scenario: the panel lives in index.html, hidden off-Ignis by styles.css, rendered by js/app.js", () => {
  assert.ok(html.includes('id="ignis-review-scenario"'));
  assert.ok(html.includes("ignis-review-scenario-panel"));
  assert.ok(css.includes(".ignis-review-scenario-panel"));
  assert.ok(css.includes('body[data-product="ignis"] .ignis-review-scenario-panel'));
  assert.ok(app.includes("ignisReviewByScenario"));
  assert.ok(app.includes('ignisReviewScenario: $("ignis-review-scenario")'));
  assert.ok(app.includes("els.ignisReviewScenario.textContent"));
});
