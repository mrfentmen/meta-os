// Meta Aegis eval harness, first slice — self-tests.
// The harness scores itself against the same committed records it replays:
// every scenario passes under the real assessor, and the baseline fails
// exactly the scenarios it should (the positive detection plus the two
// replays, which are not detections at all).
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { runAegisEval, assessReal } from "./adapter.mjs";
import { assessBaseline } from "./baseline.mjs";

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, "..", "..");
const scenarios = JSON.parse(readFileSync(join(here, "scenarios.json"), "utf8")).scenarios;

test("real assessor replays every scenario to its recorded value", async () => {
  const records = await runAegisEval(scenarios, assessReal, { root });
  assert.equal(records.length, 5);
  for (const r of records) {
    assert.equal(r.error, null, r.scenario_id + " errored: " + r.error);
    assert.equal(r.pass, true, r.scenario_id + " expected " +
      JSON.stringify(r.expected) + " got " + JSON.stringify(r.actual));
  }
});

test("baseline passes the no-detection scenarios and fails the rest", async () => {
  const records = await runAegisEval(scenarios, assessBaseline, { root });
  const byId = Object.fromEntries(records.map((r) => [r.scenario_id, r.pass]));
  assert.equal(byId["AEG-KEV-01"], true);
  assert.equal(byId["AEG-FP-01"], true);
  assert.equal(byId["AEG-PARSE-01"], false, "baseline must miss the positive detection");
  assert.equal(byId["AEG-LED-01"], false, "a replay is not a detection prediction");
  assert.equal(byId["AEG-DIFF-01"], false, "a replay is not a detection prediction");
});

test("scenario set covers one positive detection and no invented CVE", async () => {
  const positives = scenarios.filter((s) => s.fired_expected === true);
  assert.equal(positives.length, 1);
  assert.equal(positives[0].scenario_id, "AEG-PARSE-01");
  const text = readFileSync(join(here, "scenarios.json"), "utf8");
  assert.doesNotMatch(text, /CVE-\d{4}-\d{4,}/, "no CVE is invented in the fixtures");
});
