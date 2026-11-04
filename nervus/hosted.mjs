// Meta Nervus — the hosted entry point (R11-255).
//
// The registry runs this. It drives the STUB runner end to end (map, sweep, steer, ablate, delta)
// and writes every record with `stub: true`. There is no model here and no result here is
// evidence about one; the file says so in its output so a ledger reader cannot miss it.
import fs from "node:fs";
import path from "node:path";
import url from "node:url";
import { runAndFile } from "./stub-runner.mjs";
import { stateRoot } from "../agents/state-root.mjs";

const HERE = path.dirname(url.fileURLToPath(import.meta.url));
const root = path.dirname(HERE);
// Read-only payload (the image): the ledger and receipt go to the user's state
// dir, because /usr/share/metaos/agent cannot be written at run time.
const out = stateRoot(root, "nervus");
const ledger = path.join(out, "os-build", "nervus", "stub-ledger.jsonl");
fs.mkdirSync(path.dirname(ledger), { recursive: true });

console.log("nervus STUB hosted run — no model is loaded, no result is evidence");
const rows = [];
for (const op of ["map_layers", "sweep", "steer", "ablate", "evaluate_delta"]) {
  const r = runAndFile({ operation: op, params: {}, ledgerFile: ledger });
  rows.push({ op, ok: r.ok, errors: r.errors });
  console.log("  " + op + ": " + (r.ok ? "record written (stub)" : "refused: " + r.errors.join("; ")));
}
const bad = rows.filter((r) => !r.ok);
fs.writeFileSync(path.join(out, "os-build", "nervus", "hosted-receipt.json"), JSON.stringify({
  at: new Date().toISOString(), ledger: path.relative(out, ledger), rows, stub: true,
}, null, 2));
process.exit(bad.length ? 1 : 0);
