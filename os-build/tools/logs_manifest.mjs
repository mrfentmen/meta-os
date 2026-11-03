#!/usr/bin/env node
// CB-098 — file, size, sha256 and a one-line claim for every log.
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

export function parseIndexClaims(indexFile) {
  const claims = {};
  if (!indexFile || !fs.existsSync(indexFile)) return claims;
  for (const line of fs.readFileSync(indexFile, "utf8").split(/\r?\n/)) {
    if (!line.startsWith("|")) continue;
    const cells = line.split("|").slice(1, -1).map((s) => s.trim());
    if (cells.length < 4) continue;
    const file = cells[0].replace(/`/g, "");
    if (!file || file.toLowerCase() === "file") continue;
    claims[file] = cells[3] || "indexed evidence file; no note stated";
  }
  return claims;
}

export function buildLogsManifest(dir, indexFile) {
  const root = path.resolve(dir);
  const claims = parseIndexClaims(indexFile);
  return {
    root,
    generated_at: new Date().toISOString(),
    files: walk(root).map((rel) => {
      const file = path.join(root, rel);
      const st = fs.statSync(file);
      return {
        file: rel,
        size: st.size,
        sha256: sha256(file),
        claim: claims[rel] || "not indexed; no claim stated",
      };
    }),
  };
}

export function main(argv) {
  const dir = argv[0] || "os-build/logs";
  const out = argv[1] || path.join(dir, "MANIFEST-code100.json");
  const index = argv[2] || "os-build/BOOT_LOG_INDEX.md";
  const manifest = buildLogsManifest(dir, index);
  fs.writeFileSync(out, JSON.stringify(manifest, null, 2) + "\n");
  console.log("manifest: " + manifest.files.length + " files -> " + out);
}

if (process.argv[1] && import.meta.url.endsWith(process.argv[1].replace(/\\/g, "/"))) main(process.argv.slice(2));
