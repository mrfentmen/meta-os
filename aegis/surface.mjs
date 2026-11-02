// Meta Aegis — surface checks (AEGIS_SPEC.md, "Surface checks": unicode-confusable and
// invisible-character checks on shipped text and listings).
//
// Two attack shapes, both invisible to a reader and both cheap to detect:
//
//   1. A character that draws nothing but changes meaning or hides text — zero-width joiners,
//      bidi overrides, tag characters. A bidi override in a filename or an install line can
//      make a reader see one thing and execute another.
//   2. A word that looks Latin but is not: Cyrillic "а" in "pаypal". One substituted glyph is
//      invisible at reading size and defeats a copy-paste check.
//
// The output is a codepoint, a kind, and a location. Never the surrounding text: the report
// lands on a public repo, and quoting the line would republish whatever it was hiding.
export const INVISIBLE = [
  { id: "zero-width", from: 0x200b, to: 0x200f, why: "zero-width space/joiner: draws nothing, splits or joins tokens" },
  { id: "invisible-operator", from: 0x2060, to: 0x2064, why: "invisible operator: a word boundary that is not there" },
  { id: "bom", from: 0xfeff, to: 0xfeff, why: "byte-order mark inside text: invisible, and can defeat an exact-match check" },
  { id: "bidi-override", from: 0x202a, to: 0x202e, why: "bidi control: reverses what is displayed versus what is stored" },
  { id: "bidi-isolate", from: 0x2066, to: 0x2069, why: "bidi isolate: same class as an override, scoped to a run" },
  { id: "tag-char", from: 0xe0000, to: 0xe007f, why: "tag character: invisible, and can carry a hidden message" },
];

// Only the scripts that impersonate Latin are listed. A full confusables table is a data
// problem, not a code problem; these ranges catch the substitution that actually gets used.
export const SCRIPT_RANGES = [
  { id: "latin", from: 0x0041, to: 0x024f },
  { id: "latin-ext", from: 0x1e00, to: 0x1eff },
  { id: "greek", from: 0x0370, to: 0x03ff },
  { id: "cyrillic", from: 0x0400, to: 0x04ff },
];

export function scriptOf(cp) {
  for (const r of SCRIPT_RANGES) if (cp >= r.from && cp <= r.to) return r.id;
  return "other";
}

export function invisibleAt(cp) {
  return INVISIBLE.find((r) => cp >= r.from && cp <= r.to) || null;
}

const isLetter = (cp) => /[\p{L}]/u.test(String.fromCodePoint(cp));

export function scanText(text, { path: relPath = "(text)" } = {}) {
  const hits = [];
  const lines = text.split("\n");
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    // Code points, not UTF-16 units: a tag character is one code point and two units.
    const cps = [...line].map((ch) => ch.codePointAt(0));
    for (let c = 0; c < cps.length; c++) {
      const rule = invisibleAt(cps[c]);
      if (rule) hits.push({ kind: rule.id, path: relPath, line: i + 1, column: c + 1, cp: cps[c], why: rule.why });
    }
    // Mixed-script tokens: a run of letters that contains Latin and Cyrillic/Greek.
    let token = [];
    const flush = () => {
      if (token.length > 1) {
        const scripts = new Set(token.map((t) => t.script).filter((s) => s !== "other"));
        const hasLatin = scripts.has("latin") || scripts.has("latin-ext");
        const hasImpostor = scripts.has("cyrillic") || scripts.has("greek");
        if (hasLatin && hasImpostor) {
          hits.push({
            kind: "mixed-script", path: relPath, line: i + 1, column: token[0].col,
            cp: token.find((t) => t.script === "cyrillic" || t.script === "greek").cp,
            why: "a token mixes Latin with " + [...scripts].filter((s) => s !== "latin" && s !== "latin-ext").join("/") + ": one glyph can be a lookalike",
          });
        }
      }
      token = [];
    };
    for (let c = 0; c < cps.length; c++) {
      if (isLetter(cps[c])) token.push({ cp: cps[c], script: scriptOf(cps[c]), col: c + 1 });
      else flush();
    }
    flush();
  }
  return hits;
}

import fs from "node:fs";
import path from "node:path";

export function scanFiles(files, { root = process.cwd() } = {}) {
  const hits = [];
  const read = [];
  const missing = [];
  for (const f of files) {
    const abs = f.startsWith("/") ? f : path.join(root, f);
    if (!fs.existsSync(abs)) { missing.push(f); continue; }
    read.push(f);
    hits.push(...scanText(fs.readFileSync(abs, "utf8"), { path: f }));
  }
  const counts = { "zero-width": 0, "invisible-operator": 0, bom: 0, "bidi-override": 0, "bidi-isolate": 0, "tag-char": 0, "mixed-script": 0 };
  for (const h of hits) counts[h.kind] += 1;
  let chars = 0;
  for (const f of read) chars += [...fs.readFileSync(f.startsWith("/") ? f : path.join(root, f), "utf8")].length;
  return { files: read, missing, hits, counts, chars };
}

const hex = (cp) => "U+" + cp.toString(16).toUpperCase().padStart(4, "0");

export function renderReport(scan, { runId, materials }) {
  const lines = [];
  const total = scan.hits.length;
  lines.push("# Aegis surface checks — " + (total ? total + " hit(s)" : "clean"));
  lines.push("");
  lines.push("Run `" + runId + "`. Materials: " + materials.map((m) => "`" + m + "`").join(", ") + ".");
  if (scan.missing.length) lines.push("");
  if (scan.missing.length) lines.push("Not found (not reviewed): " + scan.missing.map((m) => "`" + m + "`").join(", ") + ".");
  lines.push("");
  lines.push("Two shapes: characters that draw nothing, and words that look Latin but are not. **The surrounding text is never quoted** — only the codepoint, the kind, and the location, because this report is public and the line may be what the character was hiding.");
  lines.push("");
  lines.push("## Counts");
  lines.push("");
  lines.push("| kind | count |");
  lines.push("|---|---|");
  for (const [k, v] of Object.entries(scan.counts)) lines.push("| `" + k + "` | " + v + " |");
  lines.push("");
  lines.push("## Locations");
  lines.push("");
  if (!total) {
    lines.push("None: " + scan.files.length + " file(s) read" + (typeof scan.chars === "number" ? ", " + scan.chars + " characters checked" : "") + ".");
  } else {
    lines.push("| file | line | column | kind | codepoint | why |");
    lines.push("|---|---|---|---|---|---|");
    for (const h of scan.hits.slice(0, 120)) {
      lines.push("| `" + h.path + "` | " + h.line + " | " + h.column + " | `" + h.kind + "` | `" + hex(h.cp) + "` | " + h.why + " |");
    }
    if (scan.hits.length > 120) lines.push("| | | | | | (" + (scan.hits.length - 120) + " more) |");
  }
  lines.push("");
  lines.push("## What this cannot check");
  lines.push("");
  lines.push("- Whether a Latin word is *itself* a lookalike of another Latin word. That needs a");
  lines.push("  confusables table and the target word list, which is a different check.");
  lines.push("- Text rendered in an image or a PDF; only these files were read.");
  lines.push("- Intent. A zero-width joiner is legitimate in some scripts; the line number is where a");
  lines.push("  reader looks, not a verdict.");
  lines.push("");
  return lines.join("\n");
}
