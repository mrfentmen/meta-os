#!/usr/bin/env node
// CB-077 — compare two suite outputs by failure name.
import fs from "node:fs";

export function parseFailures(text) {
  const names = new Set();
  for (const raw of text.split(/\r?\n/)) {
    const line = raw.trim();
    let m = line.match(/^not ok \d+ - (.+?)(?:\s+#.*)?$/);
    if (!m) m = line.match(/^FAILED\s+(\S+?)(?:\s+-\s+.*)?$/);
    if (!m) m = line.match(/^FAIL\s+(.+)$/);
    if (m) names.add(m[1].trim());
  }
  return [...names].sort();
}

export function diffFailures(beforeText, afterText) {
  const before = new Set(parseFailures(beforeText));
  const after = new Set(parseFailures(afterText));
  return {
    added: [...after].filter((n) => !before.has(n)).sort(),
    removed: [...before].filter((n) => !after.has(n)).sort(),
  };
}

export function main(argv) {
  if (argv.length < 2) {
    console.error("usage: test_diff.mjs <before-output> <after-output>");
    process.exitCode = 2;
    return;
  }
  const diff = diffFailures(fs.readFileSync(argv[0], "utf8"), fs.readFileSync(argv[1], "utf8"));
  console.log("added failures: " + diff.added.length);
  for (const name of diff.added) console.log("  + " + name);
  console.log("removed failures: " + diff.removed.length);
  for (const name of diff.removed) console.log("  - " + name);
}

if (process.argv[1] && import.meta.url.endsWith(process.argv[1].replace(/\\/g, "/"))) main(process.argv.slice(2));
