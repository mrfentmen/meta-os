#!/usr/bin/env node
// CB-079 — write and verify a sha256 manifest for an evidence directory.
import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";

function walk(dir, base = dir) {
  const out = [];
  for (const name of fs.readdirSync(dir).sort()) {
    const file = path.join(dir, name);
    const st = fs.statSync(file);
    if (st.isDirectory()) out.push(...walk(file, base));
    else out.push(path.relative(base, file).split(path.sep).join("/"));
  }
  return out;
}

function sha256(file) {
  return crypto.createHash("sha256").update(fs.readFileSync(file)).digest("hex");
}

export function buildManifest(dir, claims = {}) {
  const root = path.resolve(dir);
  return {
    root,
    generated_at: new Date().toISOString(),
    files: walk(root).map((rel) => {
      const file = path.join(root, rel);
      const st = fs.statSync(file);
      const row = { file: rel, size: st.size, sha256: sha256(file) };
      if (claims[rel]) row.claim = claims[rel];
      return row;
    }),
  };
}

export function verifyManifest(manifest) {
  const missing = [];
  const changed = [];
  for (const row of manifest.files) {
    const file = path.join(manifest.root, row.file);
    if (!fs.existsSync(file)) { missing.push(row.file); continue; }
    const st = fs.statSync(file);
    if (st.size !== row.size || sha256(file) !== row.sha256) changed.push(row.file);
  }
  return { ok: missing.length === 0 && changed.length === 0, missing, changed };
}

export function main(argv) {
  const [mode, ...rest] = argv;
  if (mode === "write") {
    const [dir, out, claimsFile] = rest;
    if (!dir || !out) { console.error("usage: evidence_manifest.mjs write <dir> <manifest.json> [claims.json]"); process.exitCode = 2; return; }
    const claims = claimsFile ? JSON.parse(fs.readFileSync(claimsFile, "utf8")) : {};
    const manifest = buildManifest(dir, claims);
    fs.writeFileSync(out, JSON.stringify(manifest, null, 2) + "\n");
    console.log("manifest: " + manifest.files.length + " files -> " + out);
    return;
  }
  if (mode === "verify") {
    const file = rest[0];
    if (!file) { console.error("usage: evidence_manifest.mjs verify <manifest.json>"); process.exitCode = 2; return; }
    const result = verifyManifest(JSON.parse(fs.readFileSync(file, "utf8")));
    console.log("verify: " + (result.ok ? "ok" : "FAIL") + ", missing " + result.missing.length + ", changed " + result.changed.length);
    for (const name of result.missing) console.log("  missing " + name);
    for (const name of result.changed) console.log("  changed " + name);
    if (!result.ok) process.exitCode = 1;
    return;
  }
  console.error("usage: evidence_manifest.mjs write|verify ...");
  process.exitCode = 2;
}

if (process.argv[1] && import.meta.url.endsWith(process.argv[1].replace(/\\/g, "/"))) main(process.argv.slice(2));
