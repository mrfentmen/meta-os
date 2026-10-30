// Meta Trio readiness check - one command, whole repo.
//
//   node verify/check.mjs
//
// Runs every test suite in the repo, scans for committed secrets, checks
// that the web and native sides still agree on the product keys, and
// probes for a live /api/assess server on localhost:8080. Prints one
// line per check and a summary. Exit code 1 if any real check fails.
// The server probe is informational only: whether the server happens
// to be running at this moment is reported, never counted as a failure.
//
// This tool changes nothing and calls nothing external. Spark stays off.

import { spawnSync } from "node:child_process";
import { readdirSync, readFileSync, statSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const results = [];

function record(name, ok, detail) {
  results.push({ name, ok, detail });
  console.log(`${ok ? "PASS" : "FAIL"}  ${name} - ${detail}`);
}

function runSuite(name, cmd, args) {
  const r = spawnSync(cmd, args, { cwd: ROOT, encoding: "utf8", timeout: 180000 });
  const out = `${r.stdout || ""}\n${r.stderr || ""}`;
  const pass = [...out.matchAll(/pass\s+(\d+)/g)].pop();
  const fail = [...out.matchAll(/fail\s+(\d+)/g)].pop();
  const counts = pass ? `${pass[1]} passed${fail ? `, ${fail[1]} failed` : ""}` : "no counts parsed";
  record(name, r.status === 0, counts);
}

runSuite("web suite (npm test)", "npm", ["test"]);
runSuite("medicus eval harness", "node", ["--test", "eval/medicus/harness.test.mjs"]);
runSuite("assess conformance (fixture mode)", "node", [
  "--test",
  "verify/conformance/conformance.test.mjs",
]);

// --- secret scan -------------------------------------------------------
const SECRET_PATTERNS = [
  /sk-[A-Za-z0-9_-]{20,}/,
  /ghp_[A-Za-z0-9]{30,}/,
  /AKIA[0-9A-Z]{16}/,
  /(api[_-]?key|access[_-]?token)\s*[:=]\s*["'][A-Za-z0-9._-]{16,}["']/i,
];
const SKIP_DIRS = new Set([".git", "node_modules"]);
const SKIP_FILES = new Set([path.join(ROOT, "verify", "check.mjs")]); // holds the patterns
let secretHits = [];
function walk(dir) {
  for (const entry of readdirSync(dir)) {
    const full = path.join(dir, entry);
    if (SKIP_DIRS.has(entry)) continue;
    const st = statSync(full);
    if (st.isDirectory()) walk(full);
    else if (st.isFile() && st.size < 2_000_000 && !SKIP_FILES.has(full)) {
      let text;
      try {
        text = readFileSync(full, "utf8");
      } catch {
        continue;
      }
      if (SECRET_PATTERNS.some((re) => re.test(text))) {
        secretHits.push(path.relative(ROOT, full));
      }
    }
  }
}
walk(ROOT);
record(
  "secret scan",
  secretHits.length === 0,
  secretHits.length === 0 ? "no key-shaped strings found" : `hits in: ${secretHits.join(", ")}`,
);

// --- contract coherence: product keys agree across web and native -----
function extractSet(text, re) {
  return new Set([...text.matchAll(re)].map((m) => m[1]));
}
const expected = new Set(["vigiles", "ignis", "medicus"]);
const jsProducts = extractSet(
  readFileSync(path.join(ROOT, "js", "products.js"), "utf8"),
  /id:\s*"(vigiles|ignis|medicus)"/g,
);
const swiftEnum = extractSet(
  readFileSync(path.join(ROOT, "native", "Sources", "MetaTrio", "Models", "ProductConfig.swift"), "utf8"),
  /case\s+(vigiles|ignis|medicus)\b/g,
);
const sameSet = (a, b) => a.size === b.size && [...a].every((x) => b.has(x));
record(
  "contract coherence (product keys)",
  sameSet(jsProducts, expected) && sameSet(swiftEnum, expected),
  `web: ${[...jsProducts].sort().join("/")}; native: ${[...swiftEnum].sort().join("/")}`,
);

// --- live server probe (informational) --------------------------------
try {
  const res = await fetch("http://localhost:8080/api/assess", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ product: "vigiles", timestamp: new Date().toISOString(), image: "x" }),
    signal: AbortSignal.timeout(1500),
  });
  console.log(`INFO  assess server - something answered on localhost:8080 (HTTP ${res.status})`);
} catch {
  console.log("INFO  assess server - nothing answered on localhost:8080 (start it with: node server/server.mjs)");
}

const failed = results.filter((r) => !r.ok);
console.log(`\nREADINESS: ${results.length - failed.length}/${results.length} checks passing`);
process.exit(failed.length > 0 ? 1 : 0);
