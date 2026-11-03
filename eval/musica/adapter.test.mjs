// Tests for the Meta Musica eval adapter (first slice).
// The bar-boundary and rights-rule probes are rule checks, labelled
// as such: they exercise the copied constants, they are not recorded
// takes. The recorded-take checks use the real hn029 measurements
// (take-001 keeper, take-004 reject) from the committed take log.
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import {
  assessReal,
  isClone,
  keeperVerdict,
  rightsOk,
  runMusicaEval,
  validateMusicaScenarios,
  VARIATION_THRESHOLD,
} from "./adapter.mjs";

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, "..", "..");
const scenarios = JSON.parse(readFileSync(join(here, "scenarios.json"), "utf8")).scenarios;

const base = { duration_s: 7.273, repetition: 0.0, rms_dbfs: -14.0, silence_ratio: 0.0 };

test("keeper bar passes the real hn029 keeper measurement and rejects the real reject", () => {
  assert.equal(keeperVerdict({ duration_s: 7.273, repetition: 0.5, rms_dbfs: -13.8, silence_ratio: 0.0 }).verdict, "keeper");
  const rejected = keeperVerdict({ duration_s: 7.273, repetition: 1.0, rms_dbfs: -14.5, silence_ratio: 0.0 });
  assert.equal(rejected.verdict, "reject");
  assert.match(rejected.reason, /repetition 1/);
});

test("keeper bar boundaries are the keepers.py bar (rule probes, not recorded takes)", () => {
  assert.equal(keeperVerdict({ ...base, duration_s: 4.999 }).verdict, "reject");
  assert.equal(keeperVerdict({ ...base, duration_s: 12.0 }).verdict, "keeper");
  assert.equal(keeperVerdict({ ...base, rms_dbfs: -24.0 }).verdict, "keeper");
  assert.equal(keeperVerdict({ ...base, rms_dbfs: -7.9 }).verdict, "reject");
  assert.equal(keeperVerdict({ ...base, silence_ratio: 0.25 }).verdict, "reject");
  assert.equal(keeperVerdict({ ...base, repetition: 0.75 }).verdict, "reject");
  assert.equal(keeperVerdict({ ...base, repetition: 0.749 }).verdict, "keeper");
});

test("variation threshold is strict: 0.98 exactly is not a clone", () => {
  assert.equal(VARIATION_THRESHOLD, 0.98);
  assert.equal(isClone(0.9242), false);
  assert.equal(isClone(0.98), false);
  assert.equal(isClone(0.9997), true);
});

test("rights rule mirrors rights.py: empty fails, own/CC/public domain pass", () => {
  assert.equal(rightsOk(""), false);
  assert.equal(rightsOk("   "), false);
  assert.equal(rightsOk("own — generated in-studio by Meta Musica; no third-party material"), true);
  assert.equal(rightsOk("CC-BY 4.0"), true);
  assert.equal(rightsOk("public domain"), true);
  assert.equal(rightsOk("all rights reserved"), false);
});

test("scenario set validates: duplicates and missing kinds are rejected", () => {
  assert.deepEqual(validateMusicaScenarios(scenarios), []);
  assert.equal(validateMusicaScenarios([]).length, 1);
  assert.ok(validateMusicaScenarios([scenarios[0], scenarios[0]]).some((e) => e.includes("duplicate")));
  assert.ok(validateMusicaScenarios([{ scenario_id: "X" }]).some((e) => e.includes("kind")));
});

test("real replay passes every scenario against the committed records", async () => {
  const records = await runMusicaEval(scenarios, assessReal, { root });
  assert.equal(records.length, 10);
  for (const record of records) {
    assert.equal(record.pass, true, `${record.scenario_id}: ${record.detail ?? record.error}`);
    assert.equal(record.error, null);
  }
});

test("a malformed source fails only its own scenario and the run continues", async () => {
  const throwing = async (scenario) => {
    if (scenario.scenario_id === "MUS-KEEP-01") throw new Error("boom");
    return assessReal(scenario, root);
  };
  const records = await runMusicaEval(scenarios, throwing, { root });
  assert.equal(records.find((r) => r.scenario_id === "MUS-KEEP-01").error, "boom");
  assert.equal(records.filter((r) => r.pass).length, 9);
});
