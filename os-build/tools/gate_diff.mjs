#!/usr/bin/env node
// CB-093 — compare two gate logs by stage and verdict.
import fs from "node:fs";

export function parseGate(text) {
  const stages = {};
  let current = null;
  let verdict = null;
  for (const raw of text.split(/\r?\n/)) {
    const line = raw.trim();
    const m = line.match(/^==\s+(.+?)\s+==$/);
    if (m) { current = m[1]; stages[current] = { ok: 0, fail: 0, skip: 0 }; continue; }
    const v = line.match(/GATE\s+(GREEN|RED)/);
    if (v) verdict = v[1];
    if (!current) continue;
    if (/^ok\s+/.test(line)) stages[current].ok++;
    else if (/^FAIL\s+/.test(line)) stages[current].fail++;
    else if (/^SKIP\s+/.test(line)) stages[current].skip++;
  }
  return { verdict, stages };
}

export function diffGate(beforeText, afterText) {
  const before = parseGate(beforeText);
  const after = parseGate(afterText);
  const names = [...new Set([...Object.keys(before.stages), ...Object.keys(after.stages)])].sort();
  const changes = [];
  for (const name of names) {
    const a = before.stages[name] || { ok: 0, fail: 0, skip: 0 };
    const b = after.stages[name] || { ok: 0, fail: 0, skip: 0 };
    if (JSON.stringify(a) !== JSON.stringify(b)) changes.push({ stage: name, before: a, after: b });
  }
  return { before: before.verdict, after: after.verdict, verdictChanged: before.verdict !== after.verdict, changes };
}

export function main(argv) {
  if (argv.length < 2) { console.error("usage: gate_diff.mjs <before.log> <after.log>"); process.exitCode = 2; return; }
  const diff = diffGate(fs.readFileSync(argv[0], "utf8"), fs.readFileSync(argv[1], "utf8"));
  console.log("verdict: " + (diff.before || "(none)") + " -> " + (diff.after || "(none)"));
  console.log("stage changes: " + diff.changes.length);
  for (const change of diff.changes) {
    console.log("  " + change.stage + ": " + JSON.stringify(change.before) + " -> " + JSON.stringify(change.after));
  }
}

if (process.argv[1] && import.meta.url.endsWith(process.argv[1].replace(/\\/g, "/"))) main(process.argv.slice(2));
