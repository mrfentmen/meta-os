// Surfaces edge cases the per-board suites do not already pin:
// escapeHtml's full contract, every renderer surviving a missing
// input, malformed JSONL, the cap-at-zero case, and one hostile
// value escaped end to end. Pure renderers only — nothing fetches.
// Run: node --test tests/surfaces-edges.test.mjs

import test from "node:test";
import assert from "node:assert/strict";

import {
  escapeHtml,
  labBoard,
  parseHortusJsonl,
  hortusChart,
  hortusChampion,
  gateState,
  gateStatusPage,
  evidenceViewer,
  boloCard,
  timelineView,
  receiptView,
  costTicker,
  officinaBoard,
  parseCustosJsonl,
  custosBoard,
  systemsChip,
  systemsHome,
} from "../js/surfaces.js";

test("escapeHtml escapes the four markup characters and survives null/undefined", () => {
  assert.equal(escapeHtml('&<>"'), "&amp;&lt;&gt;&quot;");
  // A single quote is deliberately NOT escaped (it is not markup here).
  assert.equal(escapeHtml("it's"), "it's");
  assert.equal(escapeHtml(null), "");
  assert.equal(escapeHtml(undefined), "");
  assert.equal(escapeHtml(0), "0");
  assert.equal(escapeHtml(false), "false");
});

test("every renderer returns a string for null/undefined, never throws or leaks 'undefined'", () => {
  const emptyInputs = [
    labBoard(undefined),
    hortusChart(undefined),
    hortusChampion(undefined),
    gateStatusPage(undefined),
    evidenceViewer(undefined),
    boloCard(undefined),
    timelineView(undefined),
    receiptView(undefined),
    costTicker(undefined),
    officinaBoard(undefined),
    custosBoard(undefined),
    systemsHome(undefined),
  ];
  for (const html of emptyInputs) {
    assert.equal(typeof html, "string");
    assert.doesNotMatch(html, /\bundefined\b/);
  }
  // The parsers report an honest empty result, not a thrown error.
  assert.deepEqual(parseHortusJsonl(undefined), { series: [], skipped: 0 });
  assert.deepEqual(parseCustosJsonl(undefined), { records: [], skipped: 0 });
  assert.equal(gateState(undefined), "not prepared");
  assert.equal(systemsChip(undefined), "not built");
});

test("lab board caps a zero-cap record and never prints the claimed level", () => {
  const html = labBoard([
    { id: "e-zero", hypothesis: "Cold fusion at home", ladder_level: 7, cap: 0, status: "rejected" },
  ]);
  assert.match(html, /Level 0 \(capped\)/);
  assert.doesNotMatch(html, /Level 7/);
  assert.doesNotMatch(html, />7</);
});

test("lab board without a cap shows the recorded level, not a fake cap", () => {
  const html = labBoard([
    { id: "e-nocap", hypothesis: "No cap on record", ladder_level: 3, status: "open" },
  ]);
  assert.match(html, /Level 3/);
  assert.doesNotMatch(html, /capped/);
});

test("parseCustosJsonl skips JSON primitives and counts them, keeps object records", () => {
  const text = [
    "42",
    '"a string"',
    "true",
    "null",
    "",
    '{"record_type":"observation","tier":"kev","source":"scanner","category":"cve","ts":"2026-11-02T00:00:00Z"}',
  ].join("\n");
  const { records, skipped } = parseCustosJsonl(text);
  assert.equal(records.length, 1);
  assert.equal(records[0].tier, "kev");
  assert.equal(skipped, 4);
});

test("a hostile timeline reason is escaped end to end", () => {
  const html = timelineView({
    timeline: [{ step: "dispatch", at: "2026-11-02T00:00:00Z", reason: '"><script>alert("x")</script>' }],
  });
  assert.doesNotMatch(html, /<script>/);
  assert.match(html, /&lt;script&gt;/);
  assert.match(html, /&quot;&gt;/);
});

test("systems home drops non-object entries and never upgrades an unknown status", () => {
  const html = systemsHome([null, undefined, { name: "Lab", status: "built" }]);
  assert.equal((html.match(/systems-item/g) || []).length, 1);
  assert.match(html, /systems-chip--not built/);
  assert.doesNotMatch(html, /systems-chip--live/);
});

test("cost ticker reads numeric strings and refuses garbage as zero", () => {
  assert.match(costTicker({ calls: "5", est_cost_usd: "1.239" }), /5 calls spent/);
  assert.match(costTicker({ calls: "5", est_cost_usd: "1.239" }), /\$1\.24 spent/);
  assert.match(costTicker({ calls: "lots", est_cost_usd: "free" }), /0 calls spent/);
  assert.match(costTicker({ calls: "lots", est_cost_usd: "free" }), /\$0\.00 spent/);
});

test("officina overnight run lists at most five variant failures", () => {
  const failures = Array.from({ length: 7 }, (_, i) => ({
    job_id: `job-${i + 1}`,
    failure_reason: "did not converge",
  }));
  const html = officinaBoard([{ artefact_class: "heatsink", n_variants: 7, failures }]);
  assert.match(html, /7 variants, 7 failures/);
  for (const id of ["job-1", "job-2", "job-3", "job-4", "job-5"]) {
    assert.match(html, new RegExp(`job ${id}:`));
  }
  assert.doesNotMatch(html, /job job-6:/);
  assert.doesNotMatch(html, /job job-7:/);
});

test("gate page given a non-array files value is the honest empty state", () => {
  const html = gateStatusPage({ files: "delaney-set.json" });
  assert.match(html, /data-gate-state="not prepared"/);
  assert.match(html, /No gate files in this repo yet/);
});
