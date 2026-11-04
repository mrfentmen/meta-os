// Meta Nervus eval adapter (first slice).
//
// Nervus was already hosted on main (agents/registry.json, nervus/hosted.mjs)
// but eval/ had no nervus harness, so there was no Nervus baseline for
// "whatever raises eval scores" to be measured against. This is that first
// harness: an offline replay of committed records only.
//
// What it scores is stub honesty, not model performance. No model is loaded
// anywhere in this path, and nothing here is evidence about a model:
//   - the ledger (os-build/nervus/stub-ledger.jsonl) is 65 stub records,
//     13 per operation, every one labelled stub:true, probe
//     "stub-probe (no model)", result source "STUB";
//   - the receipt (os-build/nervus/hosted-receipt.json) covers the five
//     stub operations, all ok, stub:true;
//   - dose-windows (nervus/dose-windows.json) carries source null and no
//     zones, so no steer record may be called measured (the contract
//     module refuses it);
//   - the layer curve (nervus/layer-curve.json) is four recorded points
//     only, with no interpolation and no claim about unmeasured layers;
//   - the face feed gap (os-build/layer1/r12/NERVUS_FACE_GAP.md) is GAP:
//     named, with a stub-banner requirement, and not filled by this slice.
//
// The harness NEVER runs the hosted entry point. That run appends five
// records to the ledger and rewrites the receipt with a fresh timestamp,
// so a harness that ran it would move the very records it scores. This
// adapter only reads committed files. The read-only guard is asserted in
// adapter.test.mjs (ledger line count identical before and after a run).

import { readFileSync } from "node:fs";
import { join } from "node:path";

export const LEDGER_REL = "os-build/nervus/stub-ledger.jsonl";
export const RECEIPT_REL = "os-build/nervus/hosted-receipt.json";
export const DOSE_WINDOWS_REL = "nervus/dose-windows.json";
export const LAYER_CURVE_REL = "nervus/layer-curve.json";
export const GAP_REL = "os-build/layer1/r12/NERVUS_FACE_GAP.md";
export const REGISTRY_REL = "agents/registry.json";

function readJson(root, rel) {
  return JSON.parse(readFileSync(join(root, rel), "utf8"));
}

function readText(root, rel) {
  return readFileSync(join(root, rel), "utf8");
}

export function loadNervusData(root) {
  const ledger = readText(root, LEDGER_REL)
    .split("\n")
    .filter((line) => line.trim() !== "")
    .map((line) => JSON.parse(line));
  const receipt = readJson(root, RECEIPT_REL);
  const doseWindows = readJson(root, DOSE_WINDOWS_REL);
  const layerCurve = readJson(root, LAYER_CURVE_REL);
  const gapDoc = readText(root, GAP_REL);
  const registry = readJson(root, REGISTRY_REL);
  const entry = (registry.agents || []).find((a) => a.name === "nervus");
  return { ledger, receipt, doseWindows, layerCurve, gapDoc, registryEntry: entry };
}

function byOp(ledger, op) {
  return ledger.filter((r) => r.operation === op);
}

function fail(evidence) {
  return { pass: false, evidence };
}

function ok(evidence) {
  return { pass: true, evidence };
}

const CHECKS = {
  "all-stub"(data, expected) {
    const stub = data.ledger.filter((r) => r.stub === true).length;
    if (stub !== expected.stub || data.ledger.length !== expected.total) {
      return fail(`stub-labelled ${stub}/${data.ledger.length}, expected ${expected.stub}/${expected.total}`);
    }
    return ok(`${stub}/${data.ledger.length} records carry stub:true`);
  },
  "probe-source"(data, expected) {
    const bad = data.ledger.filter(
      (r) => r.probe !== expected.probe || r.result?.source !== expected.source,
    );
    if (bad.length > 0 || data.ledger.length !== expected.total) {
      return fail(`${bad.length} records miss the stub probe/source, total ${data.ledger.length}`);
    }
    return ok(`all ${data.ledger.length} records: probe "${expected.probe}", source "${expected.source}"`);
  },
  "receipt-ops"(data, expected) {
    const rows = data.receipt.rows || [];
    const ops = rows.map((r) => r.op);
    const okCount = rows.filter((r) => r.ok).length;
    const opsMatch = JSON.stringify(ops) === JSON.stringify(expected.ops);
    if (data.receipt.stub !== expected.stub || !opsMatch || okCount !== expected.ok) {
      return fail(`receipt stub=${data.receipt.stub}, ops=${ops.join(",")}, ok=${okCount}/${rows.length}`);
    }
    return ok(`receipt stub:true, ${rows.length} ops, all ok: ${ops.join(", ")}`);
  },
  "single-hash"(data, expected) {
    const hashes = [...new Set(data.ledger.map((r) => r.model_hash))];
    if (hashes.length !== expected.hashes.length || hashes[0] !== expected.hashes[0]) {
      return fail(`distinct model hashes: ${hashes.length}, expected exactly the stub hash`);
    }
    return ok(`1 distinct model_hash across ${data.ledger.length} records: ${hashes[0].slice(0, 12)}...`);
  },
  "sweep-ramp"(data, expected) {
    const sweeps = byOp(data.ledger, "sweep");
    const bad = sweeps.filter(
      (r) => JSON.stringify(r.result?.neurons) !== JSON.stringify(expected.neurons),
    );
    if (sweeps.length !== expected.count || bad.length > 0) {
      return fail(`sweeps ${sweeps.length}, ${bad.length} off the stub ramp`);
    }
    return ok(`all ${sweeps.length} sweeps are the stub ramp 0 / 0.01 / 0.02 over layers 0..2`);
  },
  "steer-inert"(data, expected) {
    const steers = byOp(data.ledger, "steer");
    const bad = steers.filter(
      (r) =>
        r.zone !== expected.zone ||
        r.dose !== expected.dose ||
        r.result?.changed !== expected.changed ||
        r.result?.note !== expected.note,
    );
    const windows = data.doseWindows;
    const windowsOk = windows.source === expected.doseWindowsSource &&
      JSON.stringify(windows.zones) === JSON.stringify(expected.doseWindowsZones);
    if (steers.length !== expected.count || bad.length > 0 || !windowsOk) {
      return fail(`steers ${steers.length}, ${bad.length} not inert; dose-windows source=${windows.source}`);
    }
    return ok(`all ${steers.length} steers inert, dose 1, changed:false; dose-windows source null, zones empty, so none is called measured`);
  },
  "delta-zero"(data, expected) {
    const deltas = byOp(data.ledger, "evaluate_delta");
    const bad = deltas.filter(
      (r) =>
        r.result?.delta !== expected.delta ||
        r.before_hash !== expected.before_hash ||
        r.after_hash !== expected.after_hash,
    );
    if (deltas.length !== expected.count || bad.length > 0) {
      return fail(`evaluate_delta ${deltas.length}, ${bad.length} not the zero stub delta`);
    }
    return ok(`all ${deltas.length} evaluate_delta records: delta 0 on the fixed stub hashes`);
  },
  "curve-points"(data, expected) {
    const points = data.layerCurve.points || [];
    if (JSON.stringify(points) !== JSON.stringify(expected.points)) {
      return fail(`layer curve has ${points.length} points, expected exactly the 4 recorded ones`);
    }
    return ok(`layer curve is exactly 4 points: (4,4.6) (8,19.5) (16,12.8) (24,10.2); no interpolation claimed`);
  },
  "gap-named"(data, expected) {
    const hasGap = data.gapDoc.includes("Status: **GAP.**");
    const hasBanner = data.gapDoc.includes("STUB") && data.gapDoc.toLowerCase().includes("stub banner");
    if (!hasGap || !hasBanner || expected.status !== "GAP" || !expected.requiresStubBanner) {
      return fail(`gap doc states GAP=${hasGap}, stub-banner requirement=${hasBanner}`);
    }
    return ok(`gap doc states GAP and requires a STUB banner in the face feed; the gap is named, not filled`);
  },
  "registry-honest"(data, expected) {
    const entry = data.registryEntry;
    if (!entry) return fail("no nervus entry in agents/registry.json");
    const laneOk = expected.laneContains.every((s) => (entry.lane || "").includes(s));
    const cmdOk = JSON.stringify(entry.command) === JSON.stringify(expected.command);
    if (!laneOk || !cmdOk || entry.name !== expected.name) {
      return fail(`registry lane="${entry.lane}", command=${JSON.stringify(entry.command)}`);
    }
    return ok(`registry lane names the STUB contract run with no model loaded; command is the stub hosted entry`);
  },
};

export function assessReal(scenario, data) {
  const check = CHECKS[scenario.check];
  if (!check) return fail(`unknown check: ${scenario.check}`);
  return check(data, scenario.expected);
}

export function runNervusEval(scenarios, assess, { root }) {
  const data = loadNervusData(root);
  return scenarios.map((scenario) => {
    const result = assess(scenario, data);
    return { scenario, pass: result.pass, evidence: result.evidence };
  });
}

export function formatNervusReport(records, source) {
  const passed = records.filter((r) => r.pass).length;
  const lines = [
    `Meta Nervus eval — ${source}`,
    `Result: ${passed}/${records.length} scenarios passed.`,
    "",
  ];
  for (const r of records) {
    lines.push(`| ${r.scenario.id} (${r.scenario.title}) | ${r.pass ? "PASS" : "fail"} — ${r.evidence} |`);
  }
  return lines.join("\n");
}
