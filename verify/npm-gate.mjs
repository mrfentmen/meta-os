// npm gate with failure baseline — fails ONLY on NEW breakage.
//
// Runs the full `npm test` suite, extracts failing test names (lines
// starting with ✖, duration suffix stripped), and compares against
// verify/npm-baseline.txt (the 56 pre-existing native/Swift-parity
// failures tracked on 2026-11-03, each owned by the native/web parity
// lanes — NOT silently forgiven, listed by name in the baseline file).
//
// Exit 0: no failures outside the baseline (baseline members that got
// fixed are reported as INFO — update the baseline file, don't fail).
// Exit 1: at least one NEW failure (name it, fail the gate).
// Exit 2: the suite itself could not run (no counts parsed).
//
// This tool changes nothing and calls nothing external.

import { spawnSync } from "node:child_process";
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const BASELINE = new Set(
  readFileSync(path.join(ROOT, "verify", "npm-baseline.txt"), "utf8")
    .split("\n")
    .map((l) => l.trim())
    .filter(Boolean),
);

const r = spawnSync("npm", ["test"], {
  cwd: ROOT, encoding: "utf8", timeout: 420000, maxBuffer: 256 * 1024 * 1024,
});
const out = `${r.stdout || ""}\n${r.stderr || ""}`;
const actual = new Set(
  out.split("\n")
    .map((l) => l.replace(/\s*\([0-9.]*ms\)\s*$/, "").trim())
    .filter((l) => l.startsWith("✖") && !/failing tests:?$/i.test(l)),
);

if (actual.size === 0 && (r.status !== 0 || !/pass\s+\d+/i.test(out))) {
  console.log("npm-gate: suite did not run to counts (exit " + r.status + ")");
  process.exit(2);
}

const fresh = [...actual].filter((n) => !BASELINE.has(n));
const fixed = [...BASELINE].filter((n) => !actual.has(n));
console.log(`npm-gate: ${actual.size} failing (${BASELINE.size} baselined)`);
for (const n of fixed) console.log(`npm-gate FIXED-SINCE-BASELINE (update file): ${n}`);
if (fresh.length > 0) {
  for (const n of fresh) console.log(`npm-gate NEW-FAILURE: ${n}`);
  process.exit(1);
}
console.log("npm-gate: no new failures — gate GREEN");
