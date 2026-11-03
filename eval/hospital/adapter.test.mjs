// Meta Hospital eval adapter tests (first slice). Offline: nothing here
// watches a patient, orders anyone, or writes to a pack. All expected
// values come from the committed packs on main, and the read-only
// guard proves the run leaves the pack files exactly as it found
// them. The other-side gaps are asserted as measured, not patched:
// ems sends multi-casualty-summary to hospital with no matching
// hospital receive, and nypd declares receiving capacity-status from
// hospital with no matching hospital send.
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { execFileSync } from "node:child_process";
import { loadHospitalData, assessReal, runHospitalEval } from "./adapter.mjs";
import { assessBaseline } from "./baseline.mjs";

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, "..", "..");
const scenarios = JSON.parse(readFileSync(join(here, "scenarios.json"), "utf8")).scenarios;
const packPath = join(root, "os/worlds/hospital/pack.json");
const packBefore = () => readFileSync(packPath, "utf8");

test("scenarios: 11 unique ids, every source a committed file that exists", () => {
  assert.equal(scenarios.length, 11);
  assert.equal(new Set(scenarios.map((s) => s.id)).size, 11);
  for (const s of scenarios) {
    assert.ok(s.source, s.id + " needs a source");
    assert.ok(existsSync(join(root, s.source)), s.id + " source missing: " + s.source);
  }
});

test("real run passes all 11 scenarios on the committed packs", () => {
  const records = runHospitalEval(scenarios, assessReal, { root });
  const failed = records.filter((r) => !r.pass);
  assert.deepEqual(failed.map((r) => r.scenario.id), [], failed.map((r) => r.evidence).join("; "));
  assert.equal(records.length, 11);
});

test("committed validator independently accepts the Hospital pack", () => {
  const out = execFileSync("python3", [join(root, "os/worlds/validate_pack.py"), packPath], { encoding: "utf8" });
  assert.ok(out.trim() === "" || out.trim().endsWith(": OK"), out);
});

test("pack shape: 4 watchers, 5 agents, 7 alerts, 6 firstboot fields, status spec", () => {
  const data = loadHospitalData(root);
  assert.equal(data.pack.watchers.length, 4);
  assert.equal(data.pack.agents.length, 5);
  assert.equal(data.pack.alerts.length, 7);
  assert.equal(data.pack.firstboot.length, 6);
  assert.equal(data.pack.status, "spec");
  assert.equal(data.pack.version, "0.1.0");
  assert.deepEqual(data.dirFiles, ["PACK.md", "pack.json"]);
});

test("reciprocity as measured: receives 2/2, sends 2/2, no gaps on hospital's own declarations", () => {
  const data = loadHospitalData(root);
  const recvOk = data.pack.cross_world.receives.filter((r) =>
    data.others[r.from] && data.others[r.from].cross_world.sends.some((s) => s.to === "hospital" && s.kind === r.kind));
  const sentOk = data.pack.cross_world.sends.filter((s) =>
    data.others[s.to] && data.others[s.to].cross_world.receives.some((r) => r.from === "hospital" && r.kind === s.kind));
  assert.equal(recvOk.length, 2);
  assert.equal(sentOk.length, 2);
  assert.deepEqual(
    data.pack.cross_world.receives.filter((r) => !recvOk.includes(r)).map((r) => `${r.from}:${r.kind}`),
    []);
  assert.deepEqual(
    data.pack.cross_world.sends.filter((s) => !sentOk.includes(s)).map((s) => `${s.to}:${s.kind}`),
    []);
});

test("other-side declarations as measured: one unmatched inbound, one unmatched outbound", () => {
  const data = loadHospitalData(root);
  const inbound = [];
  const outbound = [];
  for (const w of ["nypd", "fdny", "ems", "mta", "dsny", "doe", "dep"]) {
    const other = data.others[w];
    if (!other || !other.cross_world) continue;
    for (const s of other.cross_world.sends || []) {
      if (s.to !== "hospital") continue;
      const match = data.pack.cross_world.receives.some((r) => r.from === w && r.kind === s.kind);
      if (!match) inbound.push(`${w}:${s.kind}`);
    }
    for (const r of other.cross_world.receives || []) {
      if (r.from !== "hospital") continue;
      const match = data.pack.cross_world.sends.some((s) => s.to === w && s.kind === r.kind);
      if (!match) outbound.push(`${w}:${r.kind}`);
    }
  }
  assert.deepEqual(inbound, ["ems:multi-casualty-summary"]);
  assert.deepEqual(outbound, ["nypd:capacity-status"]);
});

test("baseline passes exactly the one label scenario, fails the ten read scenarios", () => {
  const records = runHospitalEval(scenarios, assessBaseline, { root });
  assert.deepEqual(records.filter((r) => r.pass).map((r) => r.scenario.id), ["HOSP-STATUS-01"]);
  assert.equal(records.filter((r) => !r.pass).length, 10);
});

test("read-only guard: a full real run leaves pack.json byte-identical, and the adapter writes no repo file", () => {
  const before = packBefore();
  runHospitalEval(scenarios, assessReal, { root });
  assert.equal(packBefore(), before);
  const adapterSrc = readFileSync(join(here, "adapter.mjs"), "utf8");
  assert.ok(!adapterSrc.includes("writeFile"), "adapter must never write a file");
  assert.ok(!adapterSrc.includes("appendFile"), "adapter must never append");
});

test("mutated pack fails: dropping a never_carries entry breaks the privacy check", () => {
  const data = loadHospitalData(root);
  const mutated = JSON.parse(JSON.stringify(data));
  mutated.pack.cross_world.sends[0].never_carries = [];
  const scenario = scenarios.find((s) => s.id === "HOSP-PRIV-02");
  const result = assessReal(scenario, mutated, root);
  assert.equal(result.pass, false);
});
