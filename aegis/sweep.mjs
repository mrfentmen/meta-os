// Meta Aegis — sweep v1 (AEGIS_SPEC.md, "Sweep" + "Proof obligations").
//
// What it does, in order: walk the tree for manifests, turn the LOCKFILES into exact
// (ecosystem, name, version) references, ask the boss's OSV server about them in batches,
// and file one record per vulnerability. Then it writes a report naming every number it
// used, including the number of references it could NOT check.
//
// Three rules this file is built around:
//
//   1. **A manifest is not a finding.** Only a data source's answer becomes a record
//      (aegis/manifests.mjs says the same thing; this is where the answer arrives).
//   2. **No transport, no claim.** If the server is missing or fails, the run is BLOCKED and
//      files nothing. "Zero findings" and "no query happened" are different sentences and
//      the report must not swap them.
//   3. **A workspace member is not a dependency.** A Cargo.lock entry with no `source` is a
//      crate in this tree; asking OSV about `metaos-kernel 0.1.0` would be asking about
//      code that has never been published.
import fs from "node:fs";
import path from "node:path";
import { collectManifests, SKIP_DIRS, DEFAULT_MAX_DEPTH } from "./manifests.mjs";
import { appendFinding, readFindings, summarize, SEVERITIES } from "./findings.mjs";
import { Ledger } from "../agents/runtime.mjs";

export const SWEEP_SOURCE = "osv-mcp (boss's OSV server), tool scan_packages";
export const BATCH = 100;   // scan_packages maxItems

/* ---------- parsing ---------- */

// Cargo.lock has one [[package]] block per resolved crate. `source` absent means the crate is
// local to the workspace. Returns { queries, local } with duplicates removed.
export function parseCargoLock(text) {
  const queries = [];
  const local = [];
  const seen = new Set();
  for (const block of text.split("[[package]]").slice(1)) {
    const name = /^name = "([^"]+)"/m.exec(block);
    const version = /^version = "([^"]+)"/m.exec(block);
    const source = /^source = "([^"]+)"/m.exec(block);
    if (!name || !version) continue;
    if (!source) { local.push({ name: name[1], version: version[1] }); continue; }
    const key = name[1] + "@" + version[1];
    if (seen.has(key)) continue;
    seen.add(key);
    queries.push({ ecosystem: "crates.io", name: name[1], version: version[1] });
  }
  return { queries, local };
}

// package-lock.json v2/v3 keeps a flat `packages` map keyed by install path. The root entry
// ("") is the project itself, and a `link: true` entry is a workspace link, not a package.
export function parsePackageLock(text) {
  const doc = JSON.parse(text);
  const queries = [];
  const seen = new Set();
  const add = (name, version) => {
    if (!name || !version) return;
    const key = name + "@" + version;
    if (seen.has(key)) return;
    seen.add(key);
    queries.push({ ecosystem: "npm", name, version });
  };
  if (doc.packages && typeof doc.packages === "object") {
    for (const [k, v] of Object.entries(doc.packages)) {
      if (!k || !v || v.link) continue;
      const name = v.name || k.slice(k.lastIndexOf("node_modules/") + "node_modules/".length);
      add(name, v.version);
    }
  } else if (doc.dependencies && typeof doc.dependencies === "object") {
    for (const [name, v] of Object.entries(doc.dependencies)) { if (v && !v.link) add(name, v.version); }
  }
  return { queries, local: [] };
}

/* ---------- the server's answer ---------- */

// osv-mcp answers with prose, not JSON. The first version of this file assumed JSON, found
// nothing in a well-formed answer, and reported "zero findings" for 108 references -- a false
// clean bill of health produced by a parser that failed silently. These two shapes are the
// actual contract, and the tests below use them verbatim.
//
//   clean:  "No known vulnerabilities found across N package(s)."
//   hits:   "crates.io/ahash@0.8.12: 2 record(s)"
//           "RUSTSEC-2021-0001: <summary or 'No summary'>"
//           "Modified: 2026-..."
//
export function parseScanText(text) {
  const t = String(text || "");
  const clean = /No known vulnerabilities found across (\d+) package\(s\)/.exec(t);
  if (clean) return { clean: true, packages: Number(clean[1]), hits: [] };
  const hits = [];
  let cur = null;
  for (const raw of t.split("\n")) {
    const line = raw.trim();
    if (!line) continue;
    const head = /^([A-Za-z0-9._-]+)\/([^\s@]+)@([^\s:]+): (\d+) record\(s\)$/.exec(line);
    if (head) { cur = { ecosystem: head[1], name: head[2], version: head[3], ids: [] }; hits.push(cur); continue; }
    // GHSA ids carry lowercase (GHSA-29mw-wpgm-hmr9); RUSTSEC and CVE do not. An uppercase-only
    // class here silently dropped every GitHub advisory, which the first hit-shape test missed
    // because it only used a RUSTSEC id.
    const id = /^([A-Z][A-Z0-9]*-[A-Za-z0-9][A-Za-z0-9._-]*):/.exec(line);
    if (id && cur) { cur.ids.push(id[1]); continue; }
  }
  // A non-empty answer that is neither shape is not "clean" -- it is unparseable, and saying so
  // is the only honest outcome. Callers treat that as a blocked run.
  if (!hits.length) {
    if (!t.trim()) return { clean: false, unparseable: true, hits: [] };
    return { clean: false, unparseable: true, hits: [], raw: t.slice(0, 300) };
  }
  return { clean: false, packages: null, hits };
}

// This server publishes no severity and no fixed version. Both are named in the evidence rather
// than guessed: "not published" is a fact about the source, and a made-up "high" would be a
// claim Aegis cannot defend when someone asks which source said so.
export const NO_SEVERITY = "the source publishes no severity for this record; filed low, which is the floor and not a judgement";
export const NO_FIXED = "the source publishes no fixed version; the advisory text is the evidence";

/* ---------- the sweep ---------- */

// The collector inventories manifests that DECLARE dependencies; a lockfile records what was
// actually RESOLVED. Different question, same tree, so the same skip rules apply -- but it is
// a separate walk, and it reports what it walked.
export function findLockfiles(root, { maxDepth = DEFAULT_MAX_DEPTH, skipDirs = SKIP_DIRS } = {}) {
  const base = path.resolve(root);
  const out = [];
  const walk = (abs, depth) => {
    if (depth > maxDepth) return;
    for (const e of fs.readdirSync(abs, { withFileTypes: true })) {
      if (e.isSymbolicLink()) continue;
      const child = path.join(abs, e.name);
      if (e.isDirectory()) { if (!skipDirs.has(e.name)) walk(child, depth + 1); continue; }
      if (e.isFile() && (e.name === "Cargo.lock" || e.name === "package-lock.json")) {
        out.push(path.relative(base, child).split(path.sep).join("/"));
      }
    }
  };
  walk(base, 0);
  return out.sort();
}

export function buildPlan(root) {
  const inventory = collectManifests(root);
  const lockFiles = findLockfiles(root);
  const queries = [];
  const local = [];
  const unversioned = [];
  const unreadable = [];
  const seen = new Set();
  const addAll = (qs, file) => {
    for (const q of qs) {
      const key = q.ecosystem + ":" + q.name + "@" + q.version;
      if (seen.has(key)) continue;
      seen.add(key);
      queries.push({ ...q, from: file });
    }
  };

  for (const file of lockFiles) {
    const text = fs.readFileSync(path.join(root, file), "utf8");
    const parsed = file.endsWith("Cargo.lock") ? parseCargoLock(text) : parsePackageLock(text);
    addAll(parsed.queries, file);
    for (const l of parsed.local) local.push({ ...l, from: file });
  }

  // A package.json with no lockfile beside it has ranges, not versions. OSV cannot be asked
  // "is ^4.17.0 vulnerable", and pretending "*" is a version would be a false query.
  for (const m of inventory.manifests) {
    if (m.manifest !== "package.json") continue;
    if (lockFiles.includes(path.posix.join(path.posix.dirname(m.path), "package-lock.json"))) continue;
    let doc;
    try {
      doc = JSON.parse(fs.readFileSync(path.join(root, m.path), "utf8"));
    } catch (err) {
      // A malformed manifest used to throw out of buildPlan and take the whole sweep down, so
      // one bad file hid every other manifest's result (R11-283, gap-fill). It is now a recorded
      // skip: named, counted, and not queried.
      unreadable.push({ manifest: m.path, reason: String((err && err.message) || err).slice(0, 200) });
      continue;
    }
    const deps = { ...(doc.dependencies || {}), ...(doc.devDependencies || {}), ...(doc.optionalDependencies || {}) };
    if (Object.keys(deps).length) unversioned.push({ manifest: m.path, count: Object.keys(deps).length });
  }
  return { inventory, lockFiles, queries, local, unversioned, unreadable };
}

// `client` is injected: the real one speaks MCP (aegis/osv-client.mjs), the test's is a stub
// with the same callTool shape. That is also how "blocked" is testable without a network.
export async function runSweep({ root, outDir, client, runId, sourceServer = "unknown", now = () => new Date() }) {
  const plan = buildPlan(root);
  fs.mkdirSync(outDir, { recursive: true });
  const findingsFile = path.join(outDir, "findings.jsonl");
  const ledger = new Ledger(path.join(outDir, "runs.jsonl"));
  const startedAt = now().toISOString();
  ledger.add(runId, "sweep-start", {
    root: path.basename(root), manifests: plan.inventory.counts.total,
    lockFiles: plan.lockFiles, queries: plan.queries.length, sourceServer,
  });

  if (!client) {
    ledger.add(runId, "sweep-blocked", { reason: "no OSV server" });
    return { status: "blocked", reason: "no OSV server", plan, findings: [], checked: 0, startedAt, findingsFile };
  }

  let checked = 0;
  let batches = 0;
  let unparseable = 0;
  const findings = [];
  const seenVuln = new Set();
  const detailCache = new Map();

  const detailOf = async (id) => {
    if (detailCache.has(id)) return detailCache.get(id);
    let detail = { summary: "", aliases: "", details: "" };
    try {
      const d = await client.callTool("get_vulnerability", { id });
      const text = (d && d.text) || "";
      const first = /^[^\n]*?: (.*)$/.exec(text.split("\n")[0] || "");
      const alias = /^Aliases: (.+)$/m.exec(text);
      const det = /^Details: ([\s\S]*?)(?:\n(?:Affected packages|References|Aliases|Published|Modified):|$)/m.exec(text);
      detail = {
        summary: (first ? first[1] : "").trim().slice(0, 300),
        aliases: alias ? alias[1].trim().slice(0, 200) : "",
        details: det ? det[1].replace(/\s+/g, " ").trim().slice(0, 500) : "",
      };
    } catch (err) {
      detail = { summary: "", aliases: "", details: "", error: String(err && err.message || err).slice(0, 200) };
    }
    detailCache.set(id, detail);
    return detail;
  };

  for (let i = 0; i < plan.queries.length; i += BATCH) {
    const batch = plan.queries.slice(i, i + BATCH);
    let res;
    try {
      res = await client.callTool("scan_packages", {
        packages: batch.map((q) => ({ ecosystem: q.ecosystem, name: q.name, version: q.version })),
      });
    } catch (err) {
      // A cut mid-sweep is not a blocked sweep: some batches DID run. The record keeps the
      // checked count and every finding filed before the cut, and the status says CUT so no
      // reader can mistake the partial run for a clean one (R11-287).
      const reason = "transport failed at batch " + (batches + 1) + ": " + String((err && err.message) || err).slice(0, 200);
      ledger.add(runId, "sweep-cut", { batch: batches + 1, checked, findings: findings.length, reason });
      return {
        status: "cut", reason, plan, findings, checked, batches,
        startedAt, finishedAt: now().toISOString(), findingsFile, sourceServer, unparseable,
      };
    }
    batches += 1;
    checked += batch.length;
    const parsed = parseScanText(res && res.text);
    if (parsed.unparseable) {
      unparseable += 1;
      ledger.add(runId, "sweep-unparseable", { batch: batches, raw: parsed.raw || "(empty)" });
      continue;
    }
    for (const hit of parsed.hits) {
      const q = batch.find((b) => b.ecosystem === hit.ecosystem && b.name === hit.name && b.version === hit.version);
      if (!q) {
        // The source named a package this batch did not ask about. Record it; do not attach it
        // to a neighbour's manifest line.
        ledger.add(runId, "sweep-unmatched", { ecosystem: hit.ecosystem, name: hit.name, version: hit.version });
        continue;
      }
      for (const id of hit.ids) {
        const key = id + ":" + q.name + "@" + q.version;
        if (seenVuln.has(key)) continue;
        seenVuln.add(key);
        const d = await detailOf(id);
        const rec = appendFinding(findingsFile, {
          severity: "low",
          title: id + " affects " + q.name + " " + q.version,
          evidence: [
            d.summary || "no summary published",
            d.aliases ? "aliases: " + d.aliases : "no aliases published",
            d.details ? d.details : "no details published",
            NO_SEVERITY,
            NO_FIXED,
            d.error ? "detail fetch failed: " + d.error : "",
            "declared in " + q.from,
          ].filter(Boolean).join(" | "),
          source: SWEEP_SOURCE + " " + sourceServer,
          run: runId,
          target: q.ecosystem + ":" + q.name + "@" + q.version,
        });
        findings.push(rec);
      }
    }
  }

  ledger.add(runId, "sweep-done", {
    checked, batches, unparseable, findings: findings.length, bySeverity: summarize(findings).bySeverity,
  });
  return {
    status: "ran", plan, findings, checked, batches, unparseable, startedAt,
    finishedAt: now().toISOString(), findingsFile, sourceServer,
  };
}

/* ---------- the report ---------- */

export function renderReport(result, { runId }) {
  const { plan } = result;
  const s = summarize(result.findings);
  const lines = [];
  lines.push("# Aegis sweep v1 — " + (result.status === "ran" ? "ran, " + (result.findings.length ? s.total + " finding(s)" : "zero findings") : "BLOCKED"));
  lines.push("");
  lines.push("Run `" + runId + "`, " + (result.startedAt || "") + ". Generated by `aegis/sweep.mjs`; every number below is from that run.");
  lines.push("");
  lines.push("## Source");
  lines.push("");
  lines.push("- Data source: **" + SWEEP_SOURCE + "** — the boss's own OSV server, not a direct call to api.osv.dev.");
  lines.push("- Server reports itself as: `" + (result.sourceServer || "unknown") + "`.");
  lines.push("- MCP tool: `scan_packages`, batches of at most " + BATCH + ".");
  lines.push("");
  lines.push("## What was checked");
  lines.push("");
  lines.push("| item | count |");
  lines.push("|---|---|");
  lines.push("| manifests found | " + plan.inventory.counts.total + " |");
  lines.push("| lockfiles used | " + plan.lockFiles.length + " |");
  lines.push("| versioned references queried | " + result.checked + " |");
  lines.push("| query batches | " + (result.batches || 0) + " |");
  lines.push("| workspace members skipped (not published) | " + plan.local.length + " |");
  lines.push("| manifests with unversioned deps (not queryable) | " + plan.unversioned.length + " |");
  lines.push("| manifests unreadable (skipped, named below) | " + (plan.unreadable || []).length + " |");
  lines.push("");
  if (plan.lockFiles.length) {
    lines.push("Lockfiles: " + plan.lockFiles.map((f) => "`" + f + "`").join(", ") + ".");
    lines.push("");
  }
  if (plan.local.length) {
    lines.push("Skipped as this tree's own crates: " + [...new Set(plan.local.map((l) => l.name))].join(", ") + ".");
    lines.push("");
  }

  if ((plan.unreadable || []).length) {
    lines.push("Skipped as unreadable: " + plan.unreadable.map((u) => "`" + u.manifest + "`").join(", ") + ".");
    lines.push("");
  }

  if (result.status === "cut") {
    lines.push("## Result: CUT — partial run, nothing beyond the cut is claimed");
    lines.push("");
    lines.push("The transport failed during batch " + ((result.batches || 0) + 1) + ": " + (result.reason || "unknown") + ".");
    lines.push((result.checked || 0) + " reference(s) were queried and " + (result.findings || []).length + " finding(s) filed before the cut.");
    lines.push("This is **not** a clean result and **not** a blocked one: everything after the cut is unexamined.");
    lines.push("");
    if ((result.findings || []).length) {
      lines.push("| severity | id | target |");
      lines.push("|---|---|---|");
      for (const f of result.findings) {
        lines.push("| " + f.severity + " | " + f.title.split(" affects ")[0] + " | `" + (f.target || "") + "` |");
      }
      lines.push("");
    }
    lines.push("## Records");
    lines.push("");
    lines.push("- Findings so far: `" + path.relative(process.cwd(), result.findingsFile) + "` (append-only).");
    lines.push("- Cut receipt: `os-build/aegis/runs.jsonl`, run `" + runId + "`.");
    lines.push("");
    return lines.join("\n");
  }

  if (result.status !== "ran") {
    lines.push("## Result: BLOCKED — nothing was queried");
    lines.push("");
    lines.push("The OSV server was not reachable from this machine (" + (result.reason || "unknown reason") + ").");
    lines.push("**No vulnerability claim is made by this run, and zero findings here would be a lie**: no");
    lines.push("query was sent. Re-run where the server is available; the inventory above stands on its own.");
    lines.push("");
    return lines.join("\n");
  }

  lines.push("## Findings");
  lines.push("");
  if (!result.findings.length) {
    if (result.unparseable) {
      lines.push("**No findings, but not a clean result.** " + result.unparseable + " batch(es) were unparseable,");
      lines.push("so the checked count is a count of questions asked, not of answers received.");
    } else {
      lines.push("**Zero findings** across " + result.checked + " queried references. This is a result, not an");
      lines.push("empty section: the source answered and had nothing for these versions.");
    }
  } else {
    lines.push("| severity | id | target |");
    lines.push("|---|---|---|");
    for (const f of result.findings) {
      lines.push("| " + f.severity + " | " + f.title.split(" affects ")[0] + " | `" + (f.target || "") + "` |");
    }
    lines.push("");
    lines.push("By severity: " + SEVERITIES.map((x) => x + " " + (s.bySeverity[x] || 0)).join(", ") + ".");
  }
  lines.push("");
  lines.push("## Records");
  lines.push("");
  lines.push("- Findings: `" + path.relative(process.cwd(), result.findingsFile) + "` (append-only; `aegis/findings.mjs`).");
  lines.push("- Run receipt: `os-build/aegis/runs.jsonl`, run `" + runId + "`.");
  lines.push("");
  lines.push("## What this does not claim");
  lines.push("");
  lines.push("- No CISA KEV cross-check: that is a second source and a second run, not this one.");
  lines.push("- **No severity and no fixed version come from this source.** The server returns advisory prose");
  lines.push("  only, so every record is filed `low` with that stated in its evidence. A severity column");
  lines.push("  here would be invented, and sorting by it would sort by nothing.");
  lines.push("- Unversioned dependencies were **not** checked (see the table); a range cannot be asked of OSV.");
  lines.push("- Only the manifests listed above. The boss's other repos are other runs.");
  lines.push("- **The shipped MCP servers' manifests are not in this tree.** `mcp-gateway/backends.json` names");
  lines.push("  their install paths on the VM (`/home/hatch/workspace/mcp-servers/...`), so their `package.json`");
  lines.push("  files were not walked here. That half of the spec's sweep is a run on the machine that has them.");
  if (result.unparseable) lines.push("- " + result.unparseable + " batch(es) came back in a shape this parser did not recognise; they are logged in `runs.jsonl` and are not counted as clean.");
  lines.push("");
  return lines.join("\n");
}
