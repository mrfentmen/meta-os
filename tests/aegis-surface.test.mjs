// Aegis surface checks — invisible characters and lookalike scripts.
import test from "node:test";
import assert from "node:assert/strict";
import { scanText, scriptOf, invisibleAt, renderReport } from "../aegis/surface.mjs";

const ZWSP = "\u200b";
const BIDI = "\u202e";
const CYR_A = "\u0430";   // Cyrillic a
const LAT_A = "a";

test("U1 a zero-width character is found with its line and column", () => {
  const hits = scanText("first line\nplain" + ZWSP + "text", { path: "x.md" });
  assert.equal(hits.length, 1);
  assert.equal(hits[0].kind, "zero-width");
  assert.equal(hits[0].line, 2);
  assert.equal(hits[0].column, 6);
  assert.equal(hits[0].cp, 0x200b);
});

test("U2 a bidi override and a tag character are their own kinds", () => {
  const bidi = scanText("a" + BIDI + "b");
  assert.equal(bidi.length, 1);
  assert.equal(bidi[0].kind, "bidi-override");
  const tag = String.fromCodePoint(0xe0041);
  assert.equal(scanText("x" + tag).length, 1);
  assert.equal(scanText("x" + tag)[0].kind, "tag-char");
  assert.equal(invisibleAt(0x202e).id, "bidi-override");
});

test("U3 a word mixing Latin and Cyrillic is flagged once", () => {
  const hits = scanText("pay" + CYR_A + "pal is not paypal", { path: "x" });
  assert.equal(hits.length, 1);
  assert.equal(hits[0].kind, "mixed-script");
  assert.equal(hits[0].cp, 0x430);
});

test("U4 pure scripts and code identifiers are not flagged", () => {
  assert.equal(scanText("plain english words").length, 0);
  assert.equal(scanText("\u043f\u0440\u0438\u0432\u0435\u0442 \u043c\u0438\u0440").length, 0, "a Cyrillic sentence is not an impostor");
  assert.equal(scanText("const mixedScriptName = 1;").length, 0);
  assert.equal(scriptOf(0x430), "cyrillic");
  assert.equal(scriptOf(0x61), "latin");
});

test("U5 the report prints codepoints, never the text around them", () => {
  const scan = { files: ["x.md"], missing: [], counts: { "zero-width": 1, "invisible-operator": 0, bom: 0, "bidi-override": 0, "bidi-isolate": 0, "tag-char": 0, "mixed-script": 0 },
    hits: [{ kind: "zero-width", path: "x.md", line: 3, column: 9, cp: 0x200b, why: "draws nothing" }] };
  const md = renderReport(scan, { runId: "surface-run", materials: ["x.md"] });
  assert.match(md, /U\+200B/);
  assert.match(md, /x\.md` \| 3 \| 9/);
  assert.ok(!md.includes(ZWSP), "the invisible character itself is not embedded in the report");
});

test("U6 a clean scan says clean and names how many files were read", () => {
  const scan = { files: ["a.md", "b.md"], missing: [], counts: { "zero-width": 0, "invisible-operator": 0, bom: 0, "bidi-override": 0, "bidi-isolate": 0, "tag-char": 0, "mixed-script": 0 }, hits: [] };
  const md = renderReport(scan, { runId: "clean", materials: ["a.md", "b.md"] });
  assert.match(md, /clean/);
  assert.match(md, /2 file\(s\) read/);
});
