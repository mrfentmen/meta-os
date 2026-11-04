// Meta EMS eval adapter tests (first slice). Offline, read-only:
// nothing here dispatches a unit, moves a patient, or writes to a pack.
// All expected values come from the committed packs on main, and the
// read-only guard proves the run leaves the pack files exactly as it
// found them. The reciprocity gap is asserted as measured, not patched:
// EMS multi-casualty-summary sends to fdny and hospital are NOT
// declared as received by either destination pack.
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { execFileSync } from "node:child_process";
import { loadEmsData, assessReal, runEmsEval } from "./adapter.mjs";
import { assessBaseline } from "./baseline.mjs";

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, "..", "..");
const scenarios = JSON.parse(readFileSync(join(here, "scenarios.json"), "utf8")).scenarios;
const packPath = join(root, "os/worlds/ems/pack.json");
const packBefore = () => readFileSync(packPath, "utf8");

test("scenarios: 9 unique ids, every source a committed file that exists", () => {
  assert.equal(scenarios.length, 9);
  assert.equal(new Set(scenarios.map((s) => s.id)).size, 9);
  for (const s of scenarios) {
    assert.ok(s.source, s.id + " needs a source");
    assert.ok(existsSync(join(root, s.source)), s.id + " source missing: " + s.source);
  }
});

test("real run passes all 9 scenarios on the committed packs", () => {
  const records = runEmsEval(scenarios, assessReal, { root });
  const failed = records.filter((r) => !r.pass);
  assert.deepEqual(failed.map((r) => r.scenario.id), [], failed.map((r) => r.evidence).join("; "));
  assert.equal(records.length, 9);
});

test("committed validator independently accepts the EMS pack", () => {
  const out = execFileSync("python3", [join(root, "os/worlds/validate_pack.py"), packPath], { encoding: "utf8" });
  assert.ok(out.trim() === "" || out.trim().endsWith(": OK"), out);
});

test("pack shape: 3 watchers, 3 agents, 4 alerts, 5 firstboot fields, status spec", () => {
  const data = loadEmsData(root);
  assert.equal(data.pack.watchers.length, 3);
  assert.equal(data.pack.agents.length, 3);
  assert.equal(data.pack.alerts.length, 4);
  assert.equal(data.pack.firstboot.length, 5);
  assert.equal(data.pack.status, "spec");
  assert.equal(data.pack.version, "0.1.0");
  assert.deepEqual(data.dirFiles, ["PACK.md", "pack.json"]);
});

test("reciprocity as measured: receives 3/3, sends 1/3, two gaps named", () => {
  const data = loadEmsData(root);
  const recvOk = data.pack.cross_world.receives.filter((r) =>
    data.others[r.from].cross_world.sends.some((s) => s.to === "ems" && s.kind === r.kind));
  const sentOk = data.pack.cross_world.sends.filter((s) =>
    data.others[s.to].cross_world.receives.some((r) => r.from === "ems" && r.kind === s.kind));
  assert.equal(recvOk.length, 3);
  assert.equal(sentOk.length, 1);
  assert.deepEqual(sentOk.map((s) => `${s.to}:${s.kind}`), ["hospital:incoming-patient-summary"]);
  assert.deepEqual(
    data.pack.cross_world.sends.filter((s) => !sentOk.includes(s)).map((s) => `${s.to}:${s.kind}`),
    ["fdny:multi-casualty-summary", "hospital:multi-casualty-summary"]);
});

test("baseline passes exactly the one label scenario, fails the eight read scenarios", () => {
  const records = runEmsEval(scenarios, assessBaseline, { root });
  assert.deepEqual(records.filter((r) => r.pass).map((r) => r.scenario.id), ["EMS-STATUS-01"]);
  assert.equal(records.filter((r) => !r.pass).length, 8);
});

test("read-only guard: a full real run leaves pack.json byte-identical, and the adapter writes nothing", () => {
  const before = packBefore();
  runEmsEval(scenarios, assessReal, { root });
  assert.equal(packBefore(), before);
  const adapterSrc = readFileSync(join(here, "adapter.mjs"), "utf8");
  assert.ok(!adapterSrc.includes("appendFile"), "adapter must never append");
  assert.ok(!adapterSrc.includes("writeFile"), "adapter must never write");
});

test("mutated pack fails: dropping a never_carries entry breaks the privacy check", () => {
  const data = loadEmsData(root);
  const mutated = JSON.parse(JSON.stringify(data));
  mutated.pack.cross_world.sends[0].never_carries = [];
  const scenario = scenarios.find((s) => s.id === "EMS-PRIV-02");
  const result = assessReal(scenario, mutated, root);
  assert.equal(result.pass, false);
});
