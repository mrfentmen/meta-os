// Meta FDNY eval adapter tests (first slice). Offline: nothing here
// dispatches a unit, orders a crew, or writes to a pack. The PAR clock
// smoke runs only in a temporary directory with a fake clock. All
// expected values come from the committed packs on main, and the
// read-only guard proves the run leaves the pack files exactly as it
// found them. The reciprocity gap is asserted as measured, not
// patched: fdny declares receiving transport-status from ems, but no
// ems pack send of that kind to fdny exists.
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { execFileSync } from "node:child_process";
import { loadFdnyData, assessReal, runFdnyEval } from "./adapter.mjs";
import { assessBaseline } from "./baseline.mjs";

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, "..", "..");
const scenarios = JSON.parse(readFileSync(join(here, "scenarios.json"), "utf8")).scenarios;
const packPath = join(root, "os/worlds/fdny/pack.json");
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
  const records = runFdnyEval(scenarios, assessReal, { root });
  const failed = records.filter((r) => !r.pass);
  assert.deepEqual(failed.map((r) => r.scenario.id), [], failed.map((r) => r.evidence).join("; "));
  assert.equal(records.length, 11);
});

test("committed validator independently accepts the FDNY pack", () => {
  const out = execFileSync("python3", [join(root, "os/worlds/validate_pack.py"), packPath], { encoding: "utf8" });
  assert.ok(out.trim() === "" || out.trim().endsWith(": OK"), out);
});

test("pack shape: 4 watchers, 4 agents, 4 alerts, 7 firstboot fields, status partial", () => {
  const data = loadFdnyData(root);
  assert.equal(data.pack.watchers.length, 4);
  assert.equal(data.pack.agents.length, 4);
  assert.equal(data.pack.alerts.length, 4);
  assert.equal(data.pack.firstboot.length, 7);
  assert.equal(data.pack.status, "partial");
  assert.equal(data.pack.version, "0.1.0");
  assert.deepEqual(data.dirFiles, ["PACK.md", "pack.json", "runtime"]);
});

test("reciprocity as measured: receives 2/3, sends 2/2, one gap named", () => {
  const data = loadFdnyData(root);
  const recvOk = data.pack.cross_world.receives.filter((r) =>
    data.others[r.from].cross_world.sends.some((s) => s.to === "fdny" && s.kind === r.kind));
  const sentOk = data.pack.cross_world.sends.filter((s) =>
    data.others[s.to].cross_world.receives.some((r) => r.from === "fdny" && r.kind === s.kind));
  assert.equal(recvOk.length, 2);
  assert.equal(sentOk.length, 2);
  assert.deepEqual(
    data.pack.cross_world.receives.filter((r) => !recvOk.includes(r)).map((r) => `${r.from}:${r.kind}`),
    ["ems:transport-status"]);
});

test("PAR clock smoke passes standalone through the real check", () => {
  const data = loadFdnyData(root);
  const scenario = scenarios.find((s) => s.id === "FDNY-PAR-01");
  const result = assessReal(scenario, data, root);
  assert.equal(result.pass, true, result.evidence);
});

test("baseline passes exactly the one label scenario, fails the ten read scenarios", () => {
  const records = runFdnyEval(scenarios, assessBaseline, { root });
  assert.deepEqual(records.filter((r) => r.pass).map((r) => r.scenario.id), ["FDNY-STATUS-01"]);
  assert.equal(records.filter((r) => !r.pass).length, 10);
});

test("read-only guard: a full real run leaves pack.json byte-identical, and the adapter writes no repo file", () => {
  const before = packBefore();
  runFdnyEval(scenarios, assessReal, { root });
  assert.equal(packBefore(), before);
  const adapterSrc = readFileSync(join(here, "adapter.mjs"), "utf8");
  assert.ok(!adapterSrc.includes("writeFile"), "adapter must never write a file");
  assert.ok(!adapterSrc.includes("appendFile"), "adapter must never append");
});

test("mutated pack fails: dropping a never_carries entry breaks the privacy check", () => {
  const data = loadFdnyData(root);
  const mutated = JSON.parse(JSON.stringify(data));
  mutated.pack.cross_world.sends[0].never_carries = [];
  const scenario = scenarios.find((s) => s.id === "FDNY-PRIV-02");
  const result = assessReal(scenario, mutated, root);
  assert.equal(result.pass, false);
});
