#!/usr/bin/env node
// CB-099 — every log named in DEMO_SCRIPT beats must exist in the manifest.
import fs from "node:fs";

export function demoLogRefs(markdown) {
  const refs = new Set();
  for (const m of markdown.matchAll(/os-build\/logs\/([A-Za-z0-9_./-]+)/g)) {
    refs.add(m[1].replace(/[.,;:)]+$/, ""));
  }
  return [...refs].sort();
}

export function checkManifest(refs, manifest) {
  const files = manifest.files.map((f) => f.file);
  const missing = refs.filter((ref) => {
    if (files.includes(ref)) return false;
    return !files.some((file) => file.startsWith(ref.replace(/\/$/, "") + "/"));
  });
  return { ok: missing.length === 0, refs, missing };
}

export function main(argv) {
  const scriptFile = argv[0] || "os-build/DEMO_SCRIPT.md";
  const manifestFile = argv[1] || "os-build/logs/MANIFEST-code100.json";
  const refs = demoLogRefs(fs.readFileSync(scriptFile, "utf8"));
  const manifest = JSON.parse(fs.readFileSync(manifestFile, "utf8"));
  const result = checkManifest(refs, manifest);
  console.log("demo log refs: " + refs.length + ", missing: " + result.missing.length);
  for (const ref of result.missing) console.log("  MISSING " + ref);
  if (!result.ok) process.exitCode = 1;
}

if (process.argv[1] && import.meta.url.endsWith(process.argv[1].replace(/\\/g, "/"))) main(process.argv.slice(2));
