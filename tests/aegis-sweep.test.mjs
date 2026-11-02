// Aegis sweep v1 — the parts that can be proven without a network.
// The transport is injected, so "blocked" is a testable state and not a story, and the stubs
// below return the SERVER'S ACTUAL PROSE. The first version of the sweep expected JSON, found
// nothing in a well-formed answer, and reported a false clean bill of health; a stub with a
// made-up JSON shape would have kept agreeing with that bug.
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { parseCargoLock, parsePackageLock, parseScanText, runSweep, renderReport } from "../aegis/sweep.mjs";
import { readFindings } from "../aegis/findings.mjs";

const LOCK = `version = 4

[[package]]
name = "metaos-kernel"
version = "0.1.0"

[[package]]
name = "ahash"
version = "0.8.12"
source = "registry+https://github.com/rust-lang/crates.io-index"

[[package]]
name = "ahash"
version = "0.8.12"
source = "registry+https://github.com/rust-lang/crates.io-index"
`;

const HIT_TEXT = "crates.io/ahash@0.8.12: 1 record(s)\nRUSTSEC-2024-0001: No summary\nModified: 2026-01-01T00:00:00Z\n";
const CLEAN_TEXT = (n) => "No known vulnerabilities found across " + n + " package(s).";

test("S1 a lock entry with no source is this tree's own crate, not a dependency", () => {
  const { queries, local } = parseCargoLock(LOCK);
  assert.deepEqual(local, [{ name: "metaos-kernel", version: "0.1.0" }]);
  assert.deepEqual(queries, [{ ecosystem: "crates.io", name: "ahash", version: "0.8.12" }], "duplicates collapse");
});

test("S2 package-lock v2 skips the root entry and workspace links", () => {
  const { queries } = parsePackageLock(JSON.stringify({ packages: {
    "": { name: "root", version: "1.0.0" },
    "node_modules/left-pad": { version: "1.3.0" },
    "node_modules/ours": { link: true },
  }}));
  assert.deepEqual(queries, [{ ecosystem: "npm", name: "left-pad", version: "1.3.0" }]);
});

test("S3 the two prose shapes parse, and anything else is unparseable rather than clean", () => {
  assert.deepEqual(parseScanText(CLEAN_TEXT(3)).clean, true);
  assert.equal(parseScanText(CLEAN_TEXT(3)).packages, 3);
  const hit = parseScanText(HIT_TEXT);
  assert.equal(hit.clean, false);
  assert.deepEqual(hit.hits, [{ ecosystem: "crates.io", name: "ahash", version: "0.8.12", ids: ["RUSTSEC-2024-0001"] }]);
  // A GHSA id is lowercase after the prefix. This case exists because the first version of the
  // parser required an uppercase id and silently produced a hit with no ids.
  const ghsa = parseScanText("npm/lodash@4.17.20: 2 record(s)\nGHSA-29mw-wpgm-hmr9: No summary\nModified: 2026-01-01T00:00:00Z\nGHSA-35jh-r3h4-6jhm: No summary\n");
  assert.deepEqual(ghsa.hits[0].ids, ["GHSA-29mw-wpgm-hmr9", "GHSA-35jh-r3h4-6jhm"]);
  const odd = parseScanText("Something went sideways at the upstream");
  assert.equal(odd.clean, false);
  assert.equal(odd.unparseable, true, "an unrecognised answer must never be read as clean");
  assert.equal(parseScanText("").unparseable, true);
});

function tree() {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "aegis-sweep-"));
  fs.writeFileSync(path.join(dir, "Cargo.lock"), LOCK);
  fs.writeFileSync(path.join(dir, "package.json"), JSON.stringify({ dependencies: { "left-pad": "^1.0.0" } }));
  return dir;
}

const detailStub = {
  async callTool(name) {
    if (name === "get_vulnerability") {
      return { text: "RUSTSEC-2024-0001: a real-shaped advisory\nAliases: CVE-2024-1\nDetails: a real-shaped detail.\nAffected packages: crates.io/ahash\n" };
    }
    return { text: HIT_TEXT };
  },
};

test("S4 a hit files one record naming the source, and says the source published no severity", async () => {
  const root = tree();
  const out = path.join(root, "aegis-out");
  const calls = [];
  const client = { async callTool(name, args) { calls.push({ name, args }); return detailStub.callTool(name, args); } };
  const r = await runSweep({ root, outDir: out, client, runId: "test-run", sourceServer: "osv-mcp 1.0.0" });
  assert.equal(r.status, "ran");
  assert.equal(r.checked, 1, "only the published crate is queried");
  assert.equal(calls[0].name, "scan_packages");
  assert.equal(r.findings.length, 1);
  const f = r.findings[0];
  assert.equal(f.severity, "low");
  assert.match(f.title, /RUSTSEC-2024-0001 affects ahash 0\.8\.12/);
  assert.match(f.evidence, /a real-shaped advisory/);
  assert.match(f.evidence, /CVE-2024-1/);
  assert.match(f.evidence, /publishes no severity/);
  assert.match(f.evidence, /publishes no fixed version/);
  assert.equal(f.run, "test-run");
  assert.match(f.source, /osv-mcp/);
  const back = readFindings(path.join(out, "findings.jsonl"));
  assert.equal(back.findings.length, 1);
  assert.equal(back.torn, 0);
});

test("S5 zero findings is reported as zero, and the report says the source answered", async () => {
  const root = tree();
  const out = path.join(root, "aegis-out");
  const client = { async callTool(name, args) { return { text: CLEAN_TEXT(args.packages.length) }; } };
  const r = await runSweep({ root, outDir: out, client, runId: "clean-run", sourceServer: "osv-mcp 1.0.0" });
  const md = renderReport(r, { runId: "clean-run" });
  assert.match(md, /Zero findings/);
  assert.match(md, /the source answered and had nothing/);
  assert.doesNotMatch(md, /BLOCKED/);
});

test("S6 with no server the run is BLOCKED and files no finding at all", async () => {
  const root = tree();
  const out = path.join(root, "aegis-out");
  const r = await runSweep({ root, outDir: out, client: null, runId: "blocked-run" });
  assert.equal(r.status, "blocked");
  assert.equal(r.checked, 0);
  assert.equal(fs.existsSync(path.join(out, "findings.jsonl")), false, "a blocked run writes no findings file");
  const md = renderReport(r, { runId: "blocked-run" });
  assert.match(md, /BLOCKED/);
  assert.match(md, /No vulnerability claim is made/);
  assert.doesNotMatch(md, /Zero findings/);
});

test("S7 unversioned dependencies are counted, never queried with a made-up version", async () => {
  const root = tree();
  const out = path.join(root, "aegis-out");
  const queries = [];
  const client = { async callTool(name, args) { queries.push(...args.packages); return { text: CLEAN_TEXT(args.packages.length) }; } };
  const r = await runSweep({ root, outDir: out, client, runId: "range-run", sourceServer: "stub" });
  assert.equal(r.plan.unversioned.length, 1);
  assert.ok(queries.every((q) => q.version && q.version !== "*"), "no wildcard query was sent");
});

test("S8 an unparseable batch is not counted as a clean result", async () => {
  const root = tree();
  const out = path.join(root, "aegis-out");
  const client = { async callTool() { return { text: "upstream said something unexpected" }; } };
  const r = await runSweep({ root, outDir: out, client, runId: "odd-run", sourceServer: "stub" });
  assert.equal(r.unparseable, 1);
  const md = renderReport(r, { runId: "odd-run" });
  assert.match(md, /not a clean result/);
  assert.doesNotMatch(md, /Zero findings/);
});
