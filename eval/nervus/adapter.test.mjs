// Meta Nervus eval adapter tests (first slice). Offline, read-only:
// nothing here runs the hosted entry point, appends to the ledger, or
// rewrites the receipt. All expected values come from the committed
// records on main, and the read-only guard proves the run leaves the
// ledger exactly as it found it.
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { loadNervusData, assessReal, runNervusEval } from "./adapter.mjs";
import { assessBaseline } from "./baseline.mjs";

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, "..", "..");
const scenarios = JSON.parse(readFileSync(join(here, "scenarios.json"), "utf8")).scenarios;
const ledgerPath = join(root, "os-build", "nervus", "stub-ledger.jsonl");
const ledgerLines = () => readFileSync(ledgerPath, "utf8").split("\n").filter((l) => l.trim() !== "").length;

test("scenarios: 10 unique ids, every source a committed file that exists", () => {
  assert.equal(scenarios.length, 10);
  assert.equal(new Set(scenarios.map((s) => s.id)).size, 10);
  for (const s of scenarios) {
    assert.ok(s.source, s.id + " needs a source");
    assert.ok(existsSync(join(root, s.source)), s.id + " source missing: " + s.source);
  }
});

test("real run passes all 10 scenarios on the committed records", () => {
  const records = runNervusEval(scenarios, assessReal, { root });
  const failed = records.filter((r) => !r.pass);
  assert.deepEqual(failed.map((r) => r.scenario.id), [], failed.map((r) => r.evidence).join("; "));
  assert.equal(records.length, 10);
});

test("ledger shape: 65 records, 13 per operation, one stub hash, all STUB", () => {
  const data = loadNervusData(root);
  assert.equal(data.ledger.length, 65);
  for (const op of ["map_layers", "sweep", "steer", "ablate", "evaluate_delta"]) {
    assert.equal(data.ledger.filter((r) => r.operation === op).length, 13, op);
  }
  assert.deepEqual([...new Set(data.ledger.map((r) => r.model_hash))],
    ["3575125bd5df1fbcf57f79b9569f191353f039b3bdfd9ad35d5797347df7f131"]);
  assert.ok(data.ledger.every((r) => r.stub === true && r.result.source === "STUB"));
});

test("receipt: stub:true, five ops, all ok", () => {
  const data = loadNervusData(root);
  assert.equal(data.receipt.stub, true);
  assert.deepEqual(data.receipt.rows.map((r) => r.op),
    ["map_layers", "sweep", "steer", "ablate", "evaluate_delta"]);
  assert.ok(data.receipt.rows.every((r) => r.ok));
});

test("dose windows carry no source, so no steer is called measured", () => {
  const data = loadNervusData(root);
  assert.equal(data.doseWindows.source, null);
  assert.deepEqual(data.doseWindows.zones, {});
  assert.ok(data.ledger.filter((r) => r.operation === "steer").every((r) => r.zone === "inert"));
});

test("layer curve is exactly the four recorded points", () => {
  const data = loadNervusData(root);
  assert.deepEqual(data.layerCurve.points, [
    { layer: 4, score: 4.6 },
    { layer: 8, score: 19.5 },
    { layer: 16, score: 12.8 },
    { layer: 24, score: 10.2 },
  ]);
});

test("gap record names GAP and the stub banner requirement", () => {
  const data = loadNervusData(root);
  assert.ok(data.gapDoc.includes("Status: **GAP.**"));
  assert.ok(data.gapDoc.toLowerCase().includes("stub banner"));
});

test("baseline passes exactly the two label scenarios, fails the eight read scenarios", () => {
  const records = runNervusEval(scenarios, assessBaseline, { root });
  assert.deepEqual(records.filter((r) => r.pass).map((r) => r.scenario.id), ["NER-STUB-01", "NER-STUB-02"]);
  assert.equal(records.filter((r) => !r.pass).length, 8);
});

test("read-only guard: a full real run leaves the ledger line count unchanged, and the adapter writes nothing", () => {
  const before = ledgerLines();
  runNervusEval(scenarios, assessReal, { root });
  assert.equal(ledgerLines(), before);
  const adapterSrc = readFileSync(join(here, "adapter.mjs"), "utf8");
  assert.ok(!adapterSrc.includes("appendFile"), "adapter must never append");
  assert.ok(!adapterSrc.includes("writeFile"), "adapter must never write");
});
