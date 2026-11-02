// Meta Aegis — run the sweep (AEGIS_SPEC.md, first build: "Sweep v1").
//
//   AEGIS_OSV_MCP=/path/to/osv-mcp/dist/index.js node aegis/run-sweep.mjs
//
// The server path is an environment variable on purpose. There is no default: a sweep that
// guesses where its data comes from is a sweep whose report cannot be reproduced.
//
// Exit codes: 0 ran (zero findings included), 3 blocked, 2 bad invocation.
import fs from "node:fs";
import path from "node:path";
import { openOsv } from "./osv-client.mjs";
import { runSweep, renderReport } from "./sweep.mjs";

const root = process.env.AEGIS_ROOT ? path.resolve(process.env.AEGIS_ROOT) : process.cwd();
const outDir = path.join(root, "os-build", "aegis");
const serverPath = process.env.AEGIS_OSV_MCP;
const runId = "aegis-" + new Date().toISOString().replace(/[:.]/g, "-");

let result;
let client = null;
try {
  if (serverPath) {
    client = openOsv({ serverPath });
    const info = await client.init();
    result = await runSweep({ root, outDir, client, runId, sourceServer: (info.name || "osv-mcp") + " " + (info.version || "?") });
  } else {
    result = await runSweep({ root, outDir, client: null, runId, sourceServer: "not configured", sourceError: "AEGIS_OSV_MCP is not set" });
  }
} catch (err) {
  // A server that starts and then fails is a blocked run, not a crash with a half-written report.
  result = await runSweep({ root, outDir, client: null, runId, sourceServer: "unreachable", sourceError: String(err && err.message || err) });
} finally {
  if (client) client.close();
}

fs.mkdirSync(outDir, { recursive: true });
fs.writeFileSync(path.join(outDir, "SWEEP.md"), renderReport(result, { runId }));
const s = result.findings ? result.findings.length : 0;
console.log("aegis sweep " + runId);
console.log("  status      " + result.status + (result.reason ? " (" + result.reason + ")" : ""));
console.log("  manifests   " + result.plan.inventory.counts.total + " " + JSON.stringify(result.plan.inventory.counts.byEcosystem));
console.log("  queried     " + (result.checked || 0) + " versioned refs in " + (result.batches || 0) + " batch(es)");
console.log("  skipped     " + result.plan.local.length + " local crates, " + result.plan.unversioned.length + " unversioned manifests");
console.log("  findings    " + s);
console.log("  report      " + path.relative(process.cwd(), path.join(outDir, "SWEEP.md")));
process.exit(result.status === "ran" ? 0 : 3);
