// Node built-in test runner, no dependencies:
//   node --test tests/ignis-scenario-breakdown.test.mjs
//
// IGNIS-ONEOFONE-10 (Del's one-of-one bar, Oct 30): the Ignis
// scenario breakdown counts recorded ok Ignis assessments by the
// scenario label the operator selected (or typed) when the request
// was made — the scenario_label js/log.js record() stored on each
// entry at submit time. Real state only: failures contribute
// nothing, other products move no bucket, assessments with no
// usable scenario label count in the total and in unlabeled, and
// an empty or held session reads all zeros rather than inventing
// a scenario mix. The panel itself lives in index.html (hidden
// under Vigiles/Medicus by styles.css) and is rendered from
// log.entries() inside updateLogStats in js/app.js. No contract,
// server, or Spark-gate change.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { ignisScenarioBreakdown } from "../js/ignis-scenario-breakdown.js";

const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
const app = readFileSync(new URL("../js/app.js", import.meta.url), "utf8");

const entryWithScenario = (scenario_label) => ({
  status: "ok",
  product: "ignis",
  scenario_label,
});

test("scenario breakdown: an empty session reads all zeros", () => {
  assert.deepEqual(ignisScenarioBreakdown([]), {
    total: 0,
    unlabeled: 0,
    byScenario: {},
  });
  assert.deepEqual(ignisScenarioBreakdown(null), {
    total: 0,
    unlabeled: 0,
    byScenario: {},
  });
  assert.deepEqual(ignisScenarioBreakdown(undefined), {
    total: 0,
    unlabeled: 0,
    byScenario: {},
  });
});

test("scenario breakdown: buckets follow the scenario label stamped on each entry", () => {
  const counts = ignisScenarioBreakdown([
    entryWithScenario("Visible smoke"),
    entryWithScenario("Visible smoke"),
    entryWithScenario("Steam or fog that might be mistaken for smoke"),
    entryWithScenario("staged-fall-01"),
    entryWithScenario(null),
    entryWithScenario(undefined),
    entryWithScenario(""),
    entryWithScenario(42),
    { status: "ok", product: "ignis" },
    null,
  ]);
  assert.deepEqual(counts, {
    total: 9,
    unlabeled: 5,
    byScenario: {
      "Visible smoke": 2,
      "Steam or fog that might be mistaken for smoke": 1,
      "staged-fall-01": 1,
    },
  });
});

test("scenario breakdown: failed and other-product entries move no bucket", () => {
  const counts = ignisScenarioBreakdown([
    entryWithScenario("Visible smoke"),
    { status: "failed", product: "ignis", scenario_label: "Visible smoke" },
    { status: "error", product: "ignis", scenario_label: "Visible smoke" },
    { status: "ok", product: "vigiles", scenario_label: "Visible smoke" },
    { status: "ok", product: "medicus", scenario_label: "Visible smoke" },
  ]);
  assert.deepEqual(counts, {
    total: 1,
    unlabeled: 0,
    byScenario: { "Visible smoke": 1 },
  });
});

test("scenario breakdown: panel exists, is Ignis-only, and app.js renders it", () => {
  assert.ok(
    html.includes('class="panel ignis-scenario-breakdown-panel"'),
    "index.html carries the Ignis scenario-breakdown panel",
  );
  assert.ok(
    html.includes('id="ignis-scenario-breakdown"'),
    "index.html carries the scenario-breakdown line element",
  );
  assert.ok(
    css.includes(".ignis-scenario-breakdown-panel"),
    "styles.css carries the scenario-breakdown visibility block",
  );
  assert.ok(
    css.includes('body[data-product="ignis"] .ignis-scenario-breakdown-panel'),
    "panel shows only under Ignis",
  );
  assert.ok(
    app.includes('from "./ignis-scenario-breakdown.js"'),
    "app.js imports the scenario-breakdown module",
  );
  assert.ok(
    app.includes("ignisScenarioBreakdown(log.entries())"),
    "updateLogStats renders from log entries",
  );
  assert.ok(
    app.includes('ignisScenarioBreakdown: $("ignis-scenario-breakdown")'),
    "app.js wires the scenario-breakdown line element",
  );
});
