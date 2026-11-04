// Meta NYPD eval adapter tests (first slice). Offline: nothing here
// dispatches a unit, orders anyone, or writes to a pack. All expected
// values come from the committed packs on main, and the read-only
// guard proves the run leaves the pack files exactly as it found
// them. The reciprocity gaps are asserted as measured, not patched:
// nypd declares three receives no source pack sends, and one send no
// destination pack receives.
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { execFileSync } from "node:child_process";
import { loadNypdData, assessReal, runNypdEval } from "./adapter.mjs";
import { assessBaseline } from "./baseline.mjs";

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, "..", "..");
const scenarios = JSON.parse(readFileSync(join(here, "scenarios.json"), "utf8")).scenarios;
const packPath = join(root, "os/worlds/nypd/pack.json");
const packBefore = () => readFileSync(packPath, "utf8");

test("scenarios: 10 unique ids, every source a committed file that exists", () => {
  assert.equal(scenarios.length, 10);
  assert.equal(new Set(scenarios.map((s) => s.id)).size, 10);
  for (const s of scenarios) {
    assert.ok(s.source, s.id + " needs a source");
    assert.ok(existsSync(join(root, s.source)), s.id + " source missing: " + s.source);
  }
});

test("real run passes all 10 scenarios on the committed packs", () => {
  const records = runNypdEval(scenarios, assessReal, { root });
  const failed = records.filter((r) => !r.pass);
  assert.deepEqual(failed.map((r) => r.scenario.id), [], failed.map((r) => r.evidence).join("; "));
  assert.equal(records.length, 10);
});

test("committed validator independently accepts the NYPD pack", () => {
  const out = execFileSync("python3", [join(root, "os/worlds/validate_pack.py"), packPath], { encoding: "utf8" });
  assert.ok(out.trim() === "" || out.trim().endsWith(": OK"), out);
});

test("pack shape: 3 watchers, 4 agents, 4 alerts, 6 firstboot fields, status spec", () => {
  const data = loadNypdData(root);
  assert.equal(data.pack.watchers.length, 3);
  assert.equal(data.pack.agents.length, 4);
  assert.equal(data.pack.alerts.length, 4);
  assert.equal(data.pack.firstboot.length, 6);
  assert.equal(data.pack.status, "spec");
  assert.equal(data.pack.version, "0.1.0");
  assert.deepEqual(data.dirFiles, ["PACK.md", "pack.json"]);
});

test("reciprocity as measured: receives 0/3, sends 2/3, four gaps named", () => {
  const data = loadNypdData(root);
  const recvOk = data.pack.cross_world.receives.filter((r) =>
    data.others[r.from] && data.others[r.from].cross_world.sends.some((s) => s.to === "nypd" && s.kind === r.kind));
  const sentOk = data.pack.cross_world.sends.filter((s) =>
    data.others[s.to] && data.others[s.to].cross_world.receives.some((r) => r.from === "nypd" && r.kind === s.kind));
  assert.equal(recvOk.length, 0);
  assert.equal(sentOk.length, 2);
  assert.deepEqual(
    data.pack.cross_world.receives.filter((r) => !recvOk.includes(r)).map((r) => `${r.from}:${r.kind}`),
    ["fdny:incoming-casualty-summary", "ems:transport-status", "hospital:capacity-status"]);
  assert.deepEqual(
    data.pack.cross_world.sends.filter((s) => !sentOk.includes(s)).map((s) => `${s.to}:${s.kind}`),
    ["fdny:road-closure-summary"]);
});

test("baseline passes exactly the one label scenario, fails the nine read scenarios", () => {
  const records = runNypdEval(scenarios, assessBaseline, { root });
  assert.deepEqual(records.filter((r) => r.pass).map((r) => r.scenario.id), ["NYPD-STATUS-01"]);
  assert.equal(records.filter((r) => !r.pass).length, 9);
});

test("read-only guard: a full real run leaves pack.json byte-identical, and the adapter writes no repo file", () => {
  const before = packBefore();
  runNypdEval(scenarios, assessReal, { root });
  assert.equal(packBefore(), before);
  const adapterSrc = readFileSync(join(here, "adapter.mjs"), "utf8");
  assert.ok(!adapterSrc.includes("writeFile"), "adapter must never write a file");
  assert.ok(!adapterSrc.includes("appendFile"), "adapter must never append");
});

test("mutated pack fails: dropping a never_carries entry breaks the privacy check", () => {
  const data = loadNypdData(root);
  const mutated = JSON.parse(JSON.stringify(data));
  mutated.pack.cross_world.sends[0].never_carries = [];
  const scenario = scenarios.find((s) => s.id === "NYPD-PRIV-02");
  const result = assessReal(scenario, mutated, root);
  assert.equal(result.pass, false);
});
