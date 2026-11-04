// Meta Aegis eval adapter (first slice).
// Usage: node eval/aegis/run.mjs [--baseline] [--out <path>]
// Runs the eval/aegis scenario set against the real Aegis modules, offline.
// No live OSV call, no live KEV fetch, no model call: every scenario replays
// a committed record (see scenarios.json provenance) through the module that
// produced it, and the report says whether the replay matches the record.
// That is a regression check on the machinery, not a claim about live data:
// a passing replay means the code still reads its own records the same way,
// not that the tree is clean. The KEV catalog rows are not committed (only
// the counts are), so the KEV scenario replays against an empty catalog;
// its honest result is the recorded counts, not a live verdict.

import { readFileSync, writeFileSync, mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { readFindings, summarize } from "../../aegis/findings.mjs";
import { indexKev, crossCheck } from "../../aegis/kev.mjs";
import { diffFindings } from "../../aegis/sweep-diff.mjs";
import { parseScanText, runSweep } from "../../aegis/sweep.mjs";

function sorted(value) {
  if (Array.isArray(value)) return value.map(sorted);
  if (value && typeof value === "object") {
    return Object.fromEntries(Object.keys(value).sort().map((k) => [k, sorted(value[k])]));
  }
  return value;
}

export function deepEqual(a, b) {
  return JSON.stringify(sorted(a)) === JSON.stringify(sorted(b));
}

const SWEEP_TITLE = / affects /;

// The pinned clean set from the committed false-positive drill
// (aegis/fp-drill.mjs, run fp-drill-2026-11-02T15-00-49-200Z).
const FP_CLEAN = [
  ["left-pad", "1.3.0"],
  ["is-number", "7.0.0"],
  ["ansi-regex", "5.0.1"],
];

async function assessFpDrill() {
  const dir = mkdtempSync(join(tmpdir(), "aegis-eval-fp-"));
  try {
    const packages = { "": { name: "aegis-eval-fp", version: "1.0.0" } };
    for (const [name, version] of FP_CLEAN) packages["node_modules/" + name] = { version };
    writeFileSync(join(dir, "package-lock.json"), JSON.stringify({
      name: "aegis-eval-fp", version: "1.0.0", lockfileVersion: 3, requires: true, packages,
    }, null, 2));
    let asked = 0;
    const client = {
      async callTool(name, args) {
        if (name !== "scan_packages") throw new Error("unexpected tool " + name);
        asked = args.packages.length;
        return { text: "No known vulnerabilities found across " + asked + " package(s)." };
      },
      close() {},
    };
    const result = await runSweep({
      root: dir, outDir: join(dir, "out"), client, runId: "aegis-eval-fp",
      sourceLabel: "stub source: exact clean-answer text (eval replay of the false-positive drill)",
      sourceServer: "aegis-eval stub",
    });
    return {
      actual: { status: result.status, findings: result.findings.length, checked: result.checked },
      fired: result.findings.length > 0,
    };
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
}

export async function assessReal(scenario, { root }) {
  switch (scenario.kind) {
    case "kev-reproduction": {
      const { findings } = readFindings(join(root, "os-build", "aegis", "findings.jsonl"));
      const sweep = findings.filter((f) => SWEEP_TITLE.test(f.title || ""));
      const result = crossCheck(sweep, indexKev({ vulnerabilities: [] }));
      return {
        actual: {
          checked: result.checked,
          flagged: result.flagged,
          unchecked: result.unchecked,
          excludedNonSweep: findings.length - sweep.length,
        },
        fired: result.flagged > 0,
      };
    }
    case "ledger-summary": {
      const { findings } = readFindings(join(root, "os-build", "aegis", "findings.jsonl"));
      const summary = summarize(findings);
      return { actual: { total: summary.total, bySeverity: summary.bySeverity }, fired: null };
    }
    case "sweep-diff": {
      const doc = JSON.parse(readFileSync(join(root, "os-build", "aegis", "SWEEP_DIFF.json"), "utf8"));
      const d = diffFindings(doc.unchanged, doc.unchanged);
      return {
        actual: {
          before: d.before, after: d.after,
          added: d.added.length, removed: d.removed.length, unchanged: d.unchanged.length,
        },
        fired: null,
      };
    }
    case "fp-drill":
      return assessFpDrill();
    case "parse-hit": {
      const parsed = parseScanText(scenario.input_text);
      return { actual: { clean: parsed.clean, hits: parsed.hits }, fired: parsed.hits.length > 0 };
    }
    default:
      throw new Error("unknown Aegis eval scenario kind: " + scenario.kind);
  }
}

export async function runAegisEval(scenarios, assess, { root }) {
  const records = [];
  for (const scenario of scenarios) {
    const started = Date.now();
    try {
      const res = await assess(scenario, { root });
      const pass = res.pass !== undefined ? res.pass : deepEqual(res.actual, scenario.expected);
      records.push({
        scenario_id: scenario.scenario_id,
        title: scenario.title,
        kind: scenario.kind,
        source: scenario.source,
        expected: scenario.expected,
        actual: res.actual,
        pass,
        fired: res.fired,
        fired_expected: res.fired === null ? null : scenario.fired_expected,
        category_correct: pass,
        error: null,
        latency_ms: Date.now() - started,
      });
    } catch (err) {
      records.push({
        scenario_id: scenario.scenario_id,
        title: scenario.title,
        kind: scenario.kind,
        source: scenario.source,
        expected: scenario.expected,
        actual: null,
        pass: false,
        fired: null,
        fired_expected: null,
        category_correct: false,
        error: String((err && err.message) || err),
        latency_ms: Date.now() - started,
      });
    }
  }
  return records;
}

export function formatAegisReport(records, metrics, source) {
  const lines = [];
  lines.push("# Meta Aegis eval — first slice");
  lines.push("");
  lines.push("Source: " + source + ". Offline replay of committed records; not a live sweep.");
  lines.push("");
  lines.push("| scenario | kind | pass |");
  lines.push("|---|---|---|");
  for (const r of records) {
    lines.push("| " + r.scenario_id + " " + r.title + " | " + r.kind + " | " + (r.pass ? "yes" : "NO") + " |");
  }
  lines.push("");
  lines.push("Reproduction: " + records.filter((r) => r.pass).length + "/" + records.length + " scenarios replay to their recorded values.");
  if (metrics) {
    lines.push("Detection (scored scenarios only): TP " + metrics.true_positives +
      ", FP " + metrics.false_positives + ", TN " + metrics.true_negatives +
      ", FN " + metrics.false_negatives + "; precision " + metrics.precision +
      ", recall " + metrics.recall + ".");
  }
  for (const r of records.filter((r) => r.error)) {
    lines.push("Error " + r.scenario_id + ": " + r.error);
  }
  lines.push("");
  return lines.join("\n");
}
