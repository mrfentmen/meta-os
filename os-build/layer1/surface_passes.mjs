// R13-176..200 — surface and confusable passes over the artifacts the list names.
//
// Two scanners, both already in the tree: aegis/surface.mjs for invisible characters and
// mixed-script tokens, aegis/confusables.mjs for names that render like other names.
//
// The record carries counts, code points and line numbers. It never carries the surrounding
// text or the character itself in context: a finding is "line 42, column 7, U+0430", which is
// enough to go and look and not enough to republish a payload.
//
// An artifact that is not in the tree is recorded as MISSING. A scan of nothing is not a pass,
// and 25 rows of "0 hits" over files that were never opened would be the false clean bill of
// health this whole wing exists to prevent.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { scanFiles } from "../../aegis/surface.mjs";
import { scanNames } from "../../aegis/confusables.mjs";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..");
const OUT = path.join(ROOT, "os-build", "round13", "aegis");

// task, human label, materials (relative paths or {glob})
const TASKS = [
  ["R13-176", "README shipped text", ["README.md"]],
  ["R13-177", "site/index.html", ["site/index.html"]],
  ["R13-178", "demo script", ["os-build/DEMO_SCRIPT.md"]],
  ["R13-179", "demo captions", ["os-build/layer1/DEMO_30S.md"]],
  ["R13-180", "product listing titles", ["site/index.html", "face/index.html"]],
  ["R13-181", "product listing descriptions", ["site/index.html"]],
  ["R13-182", "face UI strings", ["face/index.html", "face/face.js"]],
  ["R13-183", "board UI strings", ["board/index.html"]],
  ["R13-184", "relay viewer strings", ["relay/index.html", "relay/relay.js"]],
  ["R13-185", "registry display names", ["agents/registry.json"]],
  ["R13-186", "world pack display text", ["os/worlds/index.json", "os/worlds.json"]],
  ["R13-187", "science-lab export text", ["labs/README.md"]],
  ["R13-188", "officina output text", ["tools/README.md"]],
  ["R13-189", "musica display text", ["os-build/MUSICA.md"]],
  ["R13-190", "nervus display text", ["nervus/tray.json", "nervus/contracts.mjs"]],
  ["R13-191", "aegis finding titles", ["os-build/aegis/findings.jsonl"]],
  ["R13-192", "status file text", ["os-build/BUFFY_ROUND13_STATUS.md"]],
  ["R13-193", "submission checklist", ["os-build/SUBMISSION_CHECKLIST.md"]],
  ["R13-194", "X post draft", ["os-build/X_POST.md", "os-build/aegis/X_POST.md"]],
  ["R13-195", "store page text", ["site/store.html", "site/index.html"]],
  ["R13-196", "goal file text", ["GOAL.md", "os-build/GOAL.md"]],
  ["R13-197", "skill descriptions", [{ glob: ".agents/skills/**/*.md" }]],
  ["R13-198", "connector doc text", [{ glob: "docs/**/*.md" }]],
  ["R13-199", "error message strings", [{ glob: "services/**/*.goose" }]],
  ["R13-200", "log banner strings", [{ glob: "services/**/*.goose" }, { glob: "kernel/src/*.rs" }]],
];

const isFile = (rel) => {
  try { return fs.statSync(path.join(ROOT, rel)).isFile(); } catch { return false; }
};

// Minimal ** and * walker. Enough for the shapes above; not a glob library.
// The first version had no `*` support and reported services/**/*.goose as missing while 200
// of those files sat in the tree -- a false gap, which is the same class of error as a false
// pass. It is stated here because the fix is the only reason those rows are scans.
const SKIP = new Set(["node_modules", ".git", "target", "vendor", "dist"]);

function matchPart(part, name) {
  if (!part.includes("*")) return part === name;
  const escaped = part.replace(/[.+^${}()|[\]\\]/g, "\\$&").replace(/\*/g, "[^/]*");
  return new RegExp("^" + escaped + "$").test(name);
}

function expand(pattern) {
  const parts = pattern.split("/");
  const walk = (dir, i) => {
    if (i === parts.length) return isFile(path.relative(ROOT, dir)) ? [path.relative(ROOT, dir)] : [];
    const part = parts[i];
    if (part === "**") {
      const out = walk(dir, i + 1);
      for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
        if (!entry.isDirectory() || SKIP.has(entry.name)) continue;
        out.push(...walk(path.join(dir, entry.name), i));
      }
      return out;
    }
    const out = [];
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      if (!matchPart(part, entry.name)) continue;
      const next = path.join(dir, entry.name);
      if (i === parts.length - 1) {
        if (entry.isFile()) out.push(path.relative(ROOT, next));
      } else if (entry.isDirectory()) {
        out.push(...walk(next, i + 1));
      }
    }
    return out;
  };
  return walk(ROOT, 0);
}

// Display names for the confusable pass: JSON `name` values, HTML title/aria-label, and quoted
// strings. A spoof hides in a name a person reads, so the names a person reads are the input.
function extractNames(text, cap = 400) {
  const names = new Set();
  for (const m of text.matchAll(/"name"\s*:\s*"([^"\n]{2,80})"/g)) names.add(m[1]);
  for (const m of text.matchAll(/<title[^>]*>([^<\n]{2,80})<\/title>/gi)) names.add(m[1]);
  for (const m of text.matchAll(/aria-label="([^"\n]{2,80})"/g)) names.add(m[1]);
  for (const m of text.matchAll(/"([A-Z][^"\n]{2,60})"/g)) names.add(m[1]);
  return [...names].slice(0, cap).map((name) => ({ name, kind: "display" }));
}

const rows = [];
for (const [task, label, materials] of TASKS) {
  const files = [];
  const missing = [];
  for (const material of materials) {
    if (typeof material === "string") {
      if (isFile(material)) files.push(material);
      else missing.push(material);
    } else {
      const found = expand(material.glob);
      if (found.length) files.push(...found);
      else missing.push(material.glob);
    }
  }
  const unique = [...new Set(files)];
  const scan = unique.length
    ? scanFiles(unique, { root: ROOT })
    : { files: [], missing, hits: [], counts: { "zero-width": 0, "invisible-operator": 0, bom: 0, "bidi-override": 0, "bidi-isolate": 0, "tag-char": 0, "mixed-script": 0 }, chars: 0 };

  // Confusables run over the names extracted from the same materials.
  const names = [];
  for (const rel of unique) {
    let text;
    try { text = fs.readFileSync(path.join(ROOT, rel), "utf8"); } catch { continue; }
    names.push(...extractNames(text));
  }
  const conf = names.length ? scanNames(names) : { scanned: 0, findings: [] };

  // Location and category only: no character, no surrounding text.
  const surfaceHits = scan.hits.map((h) => ({
    kind: h.kind, path: h.path, line: h.line, column: h.column,
    codePoint: "U+" + Number(h.cp).toString(16).toUpperCase().padStart(4, "0"),
  }));
  const confHits = conf.findings.map((f) => ({
    path: f.kind || "display", index: f.hits[0].index,
    codePoint: f.hits[0].codePoint, invisible: f.hits[0].invisible,
    mixedScript: f.mixedScript,
  }));

  rows.push({
    task,
    label,
    status: unique.length ? "SCANNED" : "ARTIFACT_MISSING",
    files: unique.length,
    missing,
    codePoints: scan.chars,
    surface: { counts: scan.counts, hits: surfaceHits.length },
    confusables: { names_scanned: conf.scanned, hits: confHits.length },
    findings: surfaceHits.concat(confHits),
  });
}

fs.mkdirSync(OUT, { recursive: true });
const out = { tool: "os-build/layer1/surface_passes.mjs", tasks: rows };
fs.writeFileSync(path.join(OUT, "SURFACE_PASSES.json"), JSON.stringify(out, null, 2) + "\n");

console.log("task      status            files  chars   surface  names  confusables  label");
for (const r of rows) {
  console.log(
    r.task.padEnd(9) + " " + r.status.padEnd(17) + String(r.files).padStart(4) + "  " +
    String(r.codePoints).padStart(6) + "  " + String(r.surface.hits).padStart(7) + "  " +
    String(r.confusables.names_scanned).padStart(5) + "  " +
    String(r.confusables.hits).padStart(11) + "  " + r.label +
    (r.missing.length ? "  [missing: " + r.missing.join(", ") + "]" : "")
  );
}
const hits = rows.reduce((n, r) => n + r.findings.length, 0);
const missing = rows.filter((r) => r.status === "ARTIFACT_MISSING").length;
console.log("\ntasks=" + rows.length + " scanned=" + (rows.length - missing) +
  " artifact_missing=" + missing + " findings=" + hits);
