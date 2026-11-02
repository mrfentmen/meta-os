// Meta Aegis — the hosted entry point (R11-235, R11-254).
//
// This is the command the registry runs for the `aegis` agent. It performs the local passes that
// need no network — the confusable scan over the gateway's shipped names, the lifecycle drill, and
// the alarm split — and writes one receipt. The OSV pass is not here: it needs the boss's server,
// and a hosted command that silently claims "blocked" as success would make the ledger lie.
//
// Exit 0 only when every local pass ran and the receipt exists.
import fs from "node:fs";
import path from "node:path";
import url from "node:url";
import { Ledger } from "../agents/runtime.mjs";
import { scanNames } from "./confusables.mjs";
import { openFinding, acknowledgeFinding, closeFinding, chainOf } from "./lifecycle.mjs";
import { classify, render, ALARM, QUIET } from "./alarm.mjs";

const HERE = path.dirname(url.fileURLToPath(import.meta.url));
const root = path.dirname(HERE);
const outDir = path.join(root, "os-build", "aegis", "r11");
fs.mkdirSync(outDir, { recursive: true });

const runId = "aegis-hosted-" + new Date().toISOString().replace(/[:.]/g, "-");
const ledger = new Ledger(path.join(root, "os-build", "aegis", "runs.jsonl"));
ledger.add(runId, "hosted-local-start", { command: "aegis/hosted.mjs" });

// The names as shipped: gateway backend prefixes and the tray's tool prefixes are the two places
// an MCP name can appear in this repo.
const backends = JSON.parse(fs.readFileSync(path.join(root, "mcp-gateway", "backends.json"), "utf8"));
const tray = JSON.parse(fs.readFileSync(path.join(root, "nervus", "tray.json"), "utf8"));
const names = [
  ...(backends.backends || []).map((b) => ({ name: b.prefix, kind: "gateway-backend" })),
  ...(tray.tools || []).map((t) => ({ name: t.prefix, kind: "tray-tool" })),
];
const confusables = scanNames(names);

// The lifecycle drill runs against a throwaway file in the run's own output dir, so the real
// findings chain is never polluted by a drill.
const drillFile = path.join(outDir, "lifecycle-drill.jsonl");
try { fs.unlinkSync(drillFile); } catch { /* first run */ }
const drill = [];
openFinding(drillFile, { id: "drill-1", title: "drill finding", severity: "low" });
drill.push(acknowledgeFinding(drillFile, "drill-1", { by: "aegis" }).ok);
drill.push(closeFinding(drillFile, "drill-1", { by: "aegis", note: "drill only" }).ok);
const chain = chainOf(drillFile, "drill-1");

const alarmSplit = {
  small: classify([{ severity: "low" }]),
  big: classify([{ severity: "high" }]),
};
if (alarmSplit.small.mode !== QUIET || alarmSplit.big.mode !== ALARM) {
  ledger.add(runId, "hosted-local-failed", { reason: "alarm split did not separate" });
  console.error("aegis hosted: alarm split failed");
  process.exit(1);
}

const receipt = {
  run: runId,
  at: new Date().toISOString(),
  confusables: { scanned: confusables.scanned, findings: confusables.findings.length },
  lifecycle: { state: chain.state, steps: drill },
  alarm: { small: alarmSplit.small.mode, big: alarmSplit.big.mode },
  note: "local passes only; the OSV sweep is a separate run and is not claimed here",
};
fs.writeFileSync(path.join(outDir, "hosted-receipt.json"), JSON.stringify(receipt, null, 2));
ledger.add(runId, "hosted-local-done", {
  confusableFindings: confusables.findings.length, lifecycleState: chain.state,
});
console.log("aegis hosted: " + confusables.findings.length + " confusable finding(s); lifecycle " + chain.state);
process.exit(0);
