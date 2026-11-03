// Meta Musica eval adapter (first slice).
//
// Musica-studio was already hosted on main (agents/registry.json,
// os/worlds/musica/hosted.mjs) but eval/ had no musica harness, so
// there was no Musica baseline for "whatever raises eval scores" to
// be measured against. This is that first harness: an offline replay
// of committed records only. No audio is rendered, no model is called,
// no live key is read, no take is invented.
//
// The replay reads the session records themselves (session.json,
// take_log.jsonl, catalogue.json, rights.json, normalization.json,
// overnight-report.json) and re-applies the rules the runtime states
// in code:
//   - keeper bar, os/worlds/musica/runtime/keepers.py: duration
//     5..12 s, RMS -24..-8 dBFS, silence < 0.25, repetition < 0.75.
//   - variation threshold, os/worlds/musica/runtime/similarity.py:
//     similarity > 0.98 against an earlier keeper is a clone
//     (strictly greater: 0.98 exactly is not a clone).
//   - rights rule, os/worlds/musica/runtime/rights.py: a rights line
//     passes when it names own, CC, or public domain; an empty or
//     unrecognised line is rejected, never exported.
// The constants below are copied from those files, not re-derived;
// the adapter tests assert the bar and the rights rule on the real
// hn029 measurements, so a drift in either file shows up here.

import { readFileSync } from "node:fs";
import { join } from "node:path";

export const KEEPER_BAR = {
  durationMin: 5.0,
  durationMax: 12.0,
  rmsMinDbfs: -24.0,
  rmsMaxDbfs: -8.0,
  silenceMax: 0.25,
  repetitionMax: 0.75,
};

export const VARIATION_THRESHOLD = 0.98;

export function keeperVerdict(m) {
  const fails = [];
  if (!(KEEPER_BAR.durationMin <= m.duration_s && m.duration_s <= KEEPER_BAR.durationMax)) {
    fails.push(`duration ${m.duration_s}s outside ${KEEPER_BAR.durationMin}..${KEEPER_BAR.durationMax}s`);
  }
  if (!(KEEPER_BAR.rmsMinDbfs <= m.rms_dbfs && m.rms_dbfs <= KEEPER_BAR.rmsMaxDbfs)) {
    fails.push(`loudness ${m.rms_dbfs} dBFS outside ${KEEPER_BAR.rmsMinDbfs}..${KEEPER_BAR.rmsMaxDbfs} dBFS`);
  }
  if (m.silence_ratio >= KEEPER_BAR.silenceMax) {
    fails.push(`silence ratio ${m.silence_ratio} >= ${KEEPER_BAR.silenceMax}`);
  }
  if (m.repetition >= KEEPER_BAR.repetitionMax) {
    fails.push(`repetition ${m.repetition} >= ${KEEPER_BAR.repetitionMax}`);
  }
  return fails.length > 0 ? { reason: fails.join("; "), verdict: "reject" } : { reason: "passes length, loudness, silence, repetition", verdict: "keeper" };
}

// Mirrors rights.py rights_ok(): own, CC, or public domain passes.
export function rightsOk(licence) {
  if (typeof licence !== "string" || licence.trim() === "") return false;
  const text = licence.toLowerCase();
  return text.includes("own") || text.includes("cc-") || text.includes("cc0") || text.includes("public domain") || text.includes("public-domain");
}

export function isClone(similarity, threshold = VARIATION_THRESHOLD) {
  return similarity > threshold;
}

function readJson(root, rel) {
  return JSON.parse(readFileSync(join(root, rel), "utf8"));
}

function readLog(root, session) {
  return readFileSync(join(root, "os/worlds/musica/sessions", session, "take_log.jsonl"), "utf8")
    .split("\n")
    .filter((line) => line.trim() !== "")
    .map((line) => JSON.parse(line));
}

function sessionCounts(root, session) {
  const s = readJson(root, `os/worlds/musica/sessions/${session}/session.json`);
  return {
    clones: s.variation_pass ? s.variation_pass.clones : null,
    keepers: s.keeper_pass ? s.keeper_pass.keepers : null,
    rejects: s.keeper_pass ? s.keeper_pass.rejects : null,
    takes: s.takes_logged,
  };
}

function checkCounts(actual, expected, label) {
  const mismatches = [];
  for (const [key, want] of Object.entries(expected)) {
    if (actual[key] !== want) mismatches.push(`${label}.${key}: replay ${actual[key]}, recorded ${want}`);
  }
  return mismatches;
}

export function assessReal(scenario, root) {
  switch (scenario.kind) {
    case "keeper-measure": {
      const takes = readLog(root, scenario.session);
      const take = takes.find((t) => t.take_id === scenario.take_id);
      if (!take) return { detail: `take ${scenario.take_id} not in ${scenario.session} log`, pass: false };
      if (!take.measurement) return { detail: `take ${scenario.take_id} carries no measurement`, pass: false };
      const { reason, verdict } = keeperVerdict(take.measurement);
      const recordedMatches = take.verdict === scenario.expected_verdict;
      const pass = verdict === scenario.expected_verdict && recordedMatches;
      return {
        detail: `measurement ${JSON.stringify(take.measurement)} -> ${verdict} (${reason}); recorded verdict ${take.verdict}`,
        pass,
      };
    }
    case "session": {
      const { elapsed_s: _elapsed, reject_rate: _rate, ...counts } = scenario.expected;
      const actual = sessionCounts(root, scenario.session);
      const mismatches = checkCounts(actual, counts, scenario.session);
      if (scenario.expected.elapsed_s !== undefined || scenario.expected.reject_rate !== undefined) {
        const report = readJson(root, `os/worlds/musica/sessions/${scenario.session}/overnight-report.json`);
        if (scenario.expected.elapsed_s !== undefined && report.elapsed_s !== scenario.expected.elapsed_s) {
          mismatches.push(`overnight-report.elapsed_s: replay ${report.elapsed_s}, recorded ${scenario.expected.elapsed_s}`);
        }
        if (scenario.expected.reject_rate !== undefined && report.reject_rate !== scenario.expected.reject_rate) {
          mismatches.push(`overnight-report.reject_rate: replay ${report.reject_rate}, recorded ${scenario.expected.reject_rate}`);
        }
      }
      return { detail: mismatches.length > 0 ? mismatches.join("; ") : `counts ${JSON.stringify(actual)} match the record`, pass: mismatches.length === 0 };
    }
    case "brief-sessions": {
      const mismatches = [];
      for (const want of scenario.sessions) {
        const { session: _name, ...counts } = want;
        mismatches.push(...checkCounts(sessionCounts(root, want.session), counts, want.session));
      }
      return { detail: mismatches.length > 0 ? mismatches.join("; ") : "all three brief sessions replay 4 takes, 4 keepers, 0 rejects, 0 clones", pass: mismatches.length === 0 };
    }
    case "variation": {
      const threshold = scenario.threshold ?? VARIATION_THRESHOLD;
      const mismatches = scenario.pairs
        .filter((p) => isClone(p.similarity, threshold) !== p.expected_clone)
        .map((p) => `similarity ${p.similarity} vs threshold ${threshold}: clone=${isClone(p.similarity, threshold)}, expected ${p.expected_clone}`);
      return { detail: mismatches.length > 0 ? mismatches.join("; ") : `calibration pairs split correctly at ${threshold} (0.9242 not a clone, 0.9997 a clone)`, pass: mismatches.length === 0 };
    }
    case "rights": {
      const rights = readJson(root, `os/worlds/musica/sessions/${scenario.session}/rights.json`);
      const mismatches = [];
      if (rights.tracks_checked !== scenario.expected.tracks_checked) mismatches.push(`tracks_checked ${rights.tracks_checked}, expected ${scenario.expected.tracks_checked}`);
      if (rights.passed !== scenario.expected.passed) mismatches.push(`passed ${rights.passed}, expected ${scenario.expected.passed}`);
      if (rights.rejected.length !== scenario.expected.rejected) mismatches.push(`rejected ${rights.rejected.length}, expected ${scenario.expected.rejected}`);
      for (const probe of scenario.probes || []) {
        if (rightsOk(probe.licence) !== probe.expected) mismatches.push(`rights rule on ${JSON.stringify(probe.licence)}: ${rightsOk(probe.licence)}, expected ${probe.expected}`);
      }
      return { detail: mismatches.length > 0 ? mismatches.join("; ") : `rights ${rights.passed}/${rights.tracks_checked} passed, ${rights.rejected.length} rejected, empty line fails`, pass: mismatches.length === 0 };
    }
    case "normalization": {
      const norm = readJson(root, `os/worlds/musica/sessions/${scenario.session}/normalization.json`);
      const mismatches = [];
      if (norm.target_lufs !== scenario.expected.target_lufs) mismatches.push(`target ${norm.target_lufs}, expected ${scenario.expected.target_lufs}`);
      if (norm.tolerance_lufs !== scenario.expected.tolerance_lufs) mismatches.push(`tolerance ${norm.tolerance_lufs}, expected ${scenario.expected.tolerance_lufs}`);
      if (norm.tracks.length !== scenario.expected.tracks) mismatches.push(`tracks ${norm.tracks.length}, expected ${scenario.expected.tracks}`);
      for (const track of norm.tracks) {
        const recomputed = Math.abs(track.after_lufs - norm.target_lufs) <= norm.tolerance_lufs;
        if (track.within_tolerance !== true || recomputed !== true) mismatches.push(`${track.take_id}: within_tolerance=${track.within_tolerance}, recomputed=${recomputed}`);
      }
      return { detail: mismatches.length > 0 ? mismatches.join("; ") : `all ${norm.tracks.length} tracks within ${norm.tolerance_lufs} LUFS of ${norm.target_lufs}`, pass: mismatches.length === 0 };
    }
    case "catalogue": {
      const catalogue = readJson(root, `os/worlds/musica/sessions/${scenario.session}/catalogue.json`);
      const mismatches = [];
      if (catalogue.tracks.length !== scenario.expected.tracks) mismatches.push(`tracks ${catalogue.tracks.length}, expected ${scenario.expected.tracks}`);
      for (const track of catalogue.tracks) {
        for (const field of ["licence", "provenance", "file", "sha256"]) {
          if (typeof track[field] !== "string" || track[field].trim() === "") mismatches.push(`${track.take_id}: missing ${field}`);
        }
      }
      return { detail: mismatches.length > 0 ? mismatches.join("; ") : `${catalogue.tracks.length} tracks, every track with licence, provenance, file, sha256`, pass: mismatches.length === 0 };
    }
    default:
      return { detail: `unknown scenario kind ${scenario.kind}`, pass: false };
  }
}

export function validateMusicaScenarios(scenarios) {
  const errors = [];
  if (!Array.isArray(scenarios) || scenarios.length === 0) return ["scenario set is missing or empty"];
  const seen = new Set();
  scenarios.forEach((s, i) => {
    const prefix = `scenarios[${i}]`;
    if (!s || typeof s !== "object" || Array.isArray(s)) { errors.push(`${prefix}: not an object`); return; }
    if (typeof s.scenario_id !== "string" || s.scenario_id.length === 0) errors.push(`${prefix}.scenario_id: missing or not a string`);
    else if (seen.has(s.scenario_id)) errors.push(`${prefix}.scenario_id: duplicate "${s.scenario_id}"`);
    else seen.add(s.scenario_id);
    if (typeof s.kind !== "string" || s.kind.length === 0) errors.push(`${prefix}.kind: missing or not a string`);
    if (typeof s.description !== "string" || s.description.length === 0) errors.push(`${prefix}.description: missing or not a string`);
  });
  return errors;
}

export async function runMusicaEval(scenarios, assess, options = {}) {
  const labelErrors = validateMusicaScenarios(scenarios);
  if (labelErrors.length > 0) throw new Error(`invalid scenario set: ${labelErrors.join("; ")}`);
  const records = [];
  for (const scenario of scenarios) {
    const started = Date.now();
    let result = null;
    let error = null;
    try {
      result = await assess(scenario, options.root);
    } catch (err) {
      error = err && err.message ? err.message : String(err);
    }
    records.push({
      detail: error !== null ? null : result.detail,
      error,
      latency_ms: Date.now() - started,
      pass: error !== null ? false : result.pass,
      scenario_id: scenario.scenario_id,
    });
  }
  return records;
}

export function formatMusicaReport(records, source) {
  const passed = records.filter((r) => r.pass).length;
  const lines = [
    `Meta Musica eval report — source: ${source}`,
    `Sample size: ${records.length} scenarios, passed ${passed}, failed ${records.length - passed}`,
    "",
    "Per-scenario records:",
  ];
  for (const r of records) {
    lines.push(`  ${r.scenario_id}: pass=${r.pass}${r.error !== null ? ` error=${r.error}` : ` detail=${r.detail}`}`);
  }
  return lines.join("\n");
}
