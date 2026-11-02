// Aegis section D drill: inventory, record, watch -- wired together, no network.
//   node os-build/layer1/aegis_drill.mjs
// Writes os-build/aegis/DRILL.json. The findings record goes to a scratch directory: a drill
// is not a sweep and must not leave security-looking records on main.
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import url from "node:url";
import { collectManifests } from "../../aegis/manifests.mjs";
import { appendFinding, readFindings, summarize } from "../../aegis/findings.mjs";
import { buildWatchTargets } from "../../aegis/watch-targets.mjs";
import { pollWatch } from "../../agents/runtime.mjs";

const HERE = path.dirname(url.fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, "../..");
const run = "aegis-drill-" + Date.now().toString(36);

const inv = collectManifests(REPO);
const scratch = fs.mkdtempSync(path.join(os.tmpdir(), "aegis-drill-"));
const findingsFile = path.join(scratch, "findings.jsonl");
appendFinding(findingsFile, {
  severity: "info",
  title: "drill record: manifest inventory",
  evidence: inv.counts.total + " manifests (" +
    Object.entries(inv.counts.byEcosystem).sort().map(([k, v]) => k + "=" + v).join(", ") +
    "), scanned " + inv.scannedDirs + " dirs, skipped " + inv.skipped.count + ", capped " + inv.capped.count,
  source: "drill only -- no external data source, not a sweep",
  run,
  target: "meta-os tree",
});
const read = readFindings(findingsFile);
if (read.torn !== 0 || read.findings.length !== 1) {
  console.error("aegis drill: record failed: torn=" + read.torn + " records=" + read.findings.length);
  process.exit(1);
}

const watch = buildWatchTargets({ repos: [REPO] });
const baseline = pollWatch(watch.targets, {});
const quiet = pollWatch(watch.targets, baseline.state);

// One deliberate change, to prove the pack is watchable by the real poller and not only
// shaped like it: a scratch page, polled before and after a write.
const page = path.join(scratch, "listing.html");
fs.writeFileSync(page, "<html>v1</html>");
const pageTargets = buildWatchTargets({ pages: [page] });
const beforePage = pollWatch(pageTargets.targets, {});
fs.writeFileSync(page, "<html>v2</html>");
fs.utimesSync(page, new Date(), new Date(Date.now() + 5000));
const afterPage = pollWatch(pageTargets.targets, beforePage.state);

const rel = (p) => (p.startsWith(REPO + path.sep) ? path.relative(REPO, p) : path.basename(p));
const report = {
  note: "Drill only: inventory, record, watch. No vulnerability data was fetched; nothing here is a security finding.",
  ts: new Date().toISOString(),
  run,
  inventory: {
    total: inv.counts.total,
    byEcosystem: inv.counts.byEcosystem,
    scannedDirs: inv.scannedDirs,
    skipped: inv.skipped.count,
    capped: inv.capped.count,
    symlinksSkipped: inv.symlinksSkipped,
    manifests: inv.manifests,
  },
  record: { file: "<scratch>", ...summarize(read.findings), torn: read.torn },
  watch: {
    targets: watch.targets.map((t) => ({ type: t.type, path: rel(t.path) })),
    missing: watch.missing.map(rel),
    quietPollChanges: quiet.changes.length,
    pageChangeDetected: afterPage.changes.length,
    pageChangeKey: afterPage.changes[0] ? afterPage.changes[0].key.replace(scratch + path.sep, "") : null,
  },
};
fs.mkdirSync(path.join(HERE, "../aegis"), { recursive: true });
fs.writeFileSync(path.join(HERE, "../aegis/DRILL.json"), JSON.stringify(report, null, 2) + "\n");

console.log("aegis drill " + run);
console.log("  manifests   " + report.inventory.total + "  " + JSON.stringify(report.inventory.byEcosystem));
console.log("  scanned     " + report.inventory.scannedDirs + " dirs, skipped " + report.inventory.skipped +
  ", capped " + report.inventory.capped + ", symlinks " + report.inventory.symlinksSkipped);
console.log("  record      1 info, torn " + report.record.torn + " (scratch: " + scratch + ")");
console.log("  watch       " + report.watch.targets.length + " targets, quiet poll " +
  report.watch.quietPollChanges + " change(s), deliberate page write detected: " + report.watch.pageChangeDetected);
console.log("  report      os-build/aegis/DRILL.json");
if (quiet.changes.length !== 0) { console.error("aegis drill: quiet poll reported changes"); process.exit(1); }
if (afterPage.changes.length !== 1) { console.error("aegis drill: deliberate write was not detected"); process.exit(1); }
console.log("  exit        ok");
