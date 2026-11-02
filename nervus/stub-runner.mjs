// Meta Nervus — the STUB runner (C1). It exists so the contracts can be exercised end to end
// without a model, and it says STUB in its output and in every record it writes.
//
// It does NOT: load a model, read tensors, steer anything, or produce a result that means
// anything about a model. The reproduction run belongs to the machine with the model
// (NEURON_SURGERY_SPEC.md, first build: "Host runner over one small model ... reproducing ONE
// published result"). Until that run exists, nothing here may be cited as evidence about a model.
import fs from "node:fs";
import path from "node:path";
import { validateRecord, OPERATIONS } from "./contracts.mjs";

const STUB = "STUB";
const HEX = "0123456789abcdef";

function stubHash(seed) {
  let h = "";
  for (let i = 0; i < 64; i++) h += HEX[(seed.charCodeAt(i % Math.max(seed.length, 1)) + i) % 16];
  return h;
}

// Deterministic, obviously fake output. `sweep` over 3 neurons returns 3 entries with values
// derived from the layer, so a test can assert shape without pretending the numbers are real.
export function runStub(operation, params = {}) {
  const op = OPERATIONS[operation];
  if (!op) throw new Error("unknown operation: " + operation);
  const base = {
    model_hash: params.model_hash || stubHash("stub-model"),
    operation,
    // A probe is mandatory for every effect, so the stub supplies one and names it as a stub.
    // The first version left it undefined, and the runner's own records failed the contract --
    // which is the contract working, but it made the stub useless for exercising the shape.
    probe: params.probe || "stub-probe (no model)",
    scope: params.scope || "neuron",
  };
  let rec;
  switch (operation) {
    case "map_layers":
      rec = { ...base, result: { layers: 12, source: STUB } };
      break;
    case "sweep":
      rec = {
        ...base,
        layer_from: params.layer_from ?? 0,
        layer_to: params.layer_to ?? 2,
        result: { neurons: Array.from({ length: (params.layer_to ?? 2) - (params.layer_from ?? 0) + 1 }, (_, i) => ({ layer: (params.layer_from ?? 0) + i, value: i * 0.01 })), source: STUB },
      };
      break;
    case "steer":
      rec = {
        ...base, layer: params.layer ?? 0, neuron: params.neuron ?? 0,
        dose: params.dose ?? 1, zone: params.zone ?? "inert",
        result: { changed: false, source: STUB, note: "no model was loaded" },
      };
      break;
    case "ablate":
      rec = { ...base, layer: params.layer ?? 0, neuron: params.neuron ?? 0, result: { changed: false, source: STUB } };
      break;
    case "evaluate_delta":
      rec = {
        ...base,
        before_hash: params.before_hash || stubHash("before"),
        after_hash: params.after_hash || stubHash("after"),
        result: { delta: 0, source: STUB },
      };
      break;
    default:
      throw new Error("unhandled operation: " + operation);
  }
  return rec;
}

export function runAndFile({ operation, params, ledgerFile, doseWindows = null }) {
  const rec = runStub(operation, params);
  const errors = validateRecord(rec, { doseWindows });
  if (errors.length) return { ok: false, errors, record: rec };
  fs.mkdirSync(path.dirname(ledgerFile), { recursive: true });
  fs.appendFileSync(ledgerFile, JSON.stringify({ ...rec, stub: true }) + "\n");
  return { ok: true, errors: [], record: rec };
}

if (process.argv[1] && path.resolve(process.argv[1]) === path.resolve(new URL(import.meta.url).pathname)) {
  const [, , operation = "map_layers", ledger = "nervus-ledger.jsonl"] = process.argv;
  const r = runAndFile({ operation, params: {}, ledgerFile: ledger });
  console.log("nervus STUB runner — no model was loaded, no result here is evidence");
  console.log(r.ok ? "  record written to " + ledger : "  refused: " + r.errors.join("; "));
  process.exit(r.ok ? 0 : 1);
}
